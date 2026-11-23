from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta, timezone as datetime_timezone
from threading import Barrier
from unittest import skipUnless

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.common.test_data import clinic_data
from apps.providers.models import Provider
from apps.register.models import User

from .models import Appointment, ClinicRoom, Slot
from .services import book_appointment, cancel_appointment, save_slot


class AvailabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin, cls.patient, cls.provider, cls.slot, _ = clinic_data()
        other_account = User.objects.create_user(
            "TEST-OTHER-PROVIDER", "other-provider@example.invalid",
            user_type=User.UserType.PROVIDER, fname="Other", lname="Provider",
        )
        cls.other_provider = Provider.objects.create(
            provider=other_account, provider_type=Provider.Type.DENTIST, is_active=True,
        )
        cls.other_room = ClinicRoom.objects.create(campus="Fictional", building="Test", room_number="102")
        cls.start = datetime.combine(timezone.localdate() + timedelta(days=3), time(0, 15), timezone.get_default_timezone())
        cls.end = cls.start + timedelta(minutes=30)

    def slot_values(self, **changes):
        return {
            "actor": self.admin, "provider_id": self.provider.pk, "room_id": self.slot.room_id,
            "start_time": self.start, "end_time": self.end, "is_active": True, **changes,
        }

    def post_data(self, slot=None, **changes):
        local_input = "%Y-%m-%dT%H:%M:%S"
        data = {
            "provider": self.provider.pk, "room": self.slot.room_id,
            "start_time": self.start.strftime(local_input), "end_time": self.end.strftime(local_input),
            "is_active": "on",
        }
        if slot:
            data.update(
                expected_version=slot.version, provider=slot.provider_id, room=slot.room_id or "",
                start_time=timezone.localtime(slot.start_time).strftime(local_input),
                end_time=timezone.localtime(slot.end_time).strftime(local_input),
            )
        return {**data, **changes}

    def test_admin_creates_and_filters_by_the_manila_start_date(self):
        self.client.force_login(self.admin)
        create = reverse("availability:create")
        listing = reverse("availability:list")
        self.assertContains(self.client.get(create), "Manila time")
        self.assertRedirects(self.client.post(create, self.post_data()), listing)
        saved = Slot.objects.exclude(pk=self.slot.pk).get()
        self.assertEqual(saved.start_time, self.start.astimezone(datetime_timezone.utc))
        self.assertNotEqual(saved.start_time.date(), self.start.date())
        response = self.client.get(listing, {
            "provider": self.provider.pk, "from_date": self.start.date(), "through_date": self.start.date(),
        })
        self.assertEqual([slot.pk for slot in response.context["page_obj"]], [saved.pk])
        self.assertContains(response, "12:15:00 AM")
        bad = self.client.get(listing, {"from_date": self.end.date(), "through_date": self.end.date() - timedelta(days=1)})
        self.assertContains(bad, "Choose a date on or after From date.")
        self.assertTrue(AuditLog.objects.filter(actor_user=self.admin, target_table="slot",
            target_record_id=saved.pk, action_performed="Availability created").exists())

    def test_provider_only_lists_or_edits_own_slots_even_with_forged_ids(self):
        other_slot = save_slot(**self.slot_values(provider_id=self.other_provider.pk))
        user = self.provider.provider
        self.client.force_login(user)
        listing = reverse("availability:list")
        response = self.client.get(listing, {"provider": self.other_provider.pk})
        self.assertEqual([slot.pk for slot in response.context["page_obj"]], [self.slot.pk])
        self.assertNotContains(response, self.other_provider.provider.school_id)
        foreign_url = reverse("availability:edit", args=[other_slot.pk])
        self.assertEqual(self.client.get(foreign_url).status_code, 404)
        self.assertEqual(self.client.post(foreign_url, self.post_data(other_slot)).status_code, 404)
        self.assertRedirects(self.client.post(reverse("availability:create"), self.post_data(
            room=self.other_room.pk, provider=self.other_provider.pk,
        )), listing)
        self.assertTrue(Slot.objects.filter(provider=self.provider, room=self.other_room).exists())
        with self.assertRaises(PermissionDenied):
            save_slot(**self.slot_values(actor=user, provider_id=self.other_provider.pk))
        with self.assertRaises(PermissionDenied):
            save_slot(**self.slot_values(actor=user, slot_id=other_slot.pk, room_id=self.other_room.pk))

    def test_patient_and_inactive_provider_cannot_access_availability(self):
        listing = reverse("availability:list")
        create = reverse("availability:create")
        edit = reverse("availability:edit", args=[self.slot.pk])
        self.assertEqual(self.client.get(listing).status_code, 302)
        Provider.objects.filter(pk=self.provider.pk).update(is_active=False)
        for user in (self.patient.patient, self.provider.provider):
            self.client.force_login(user)
            self.assertEqual(self.client.get(listing).status_code, 403)
            self.assertEqual(self.client.get(edit).status_code, 403)
            self.assertEqual(self.client.post(create, self.post_data()).status_code, 403)
            self.assertNotContains(self.client.get(reverse("home:home")), f'href="{listing}"')

    def test_create_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        url = reverse("availability:create")
        self.assertEqual(client.get(url).status_code, 200)
        self.assertEqual(client.post(url, self.post_data()).status_code, 403)
        self.assertEqual(Slot.objects.count(), 1)

    def test_overlapping_room_and_provider_fail_and_adjacent_slots_work(self):
        first = save_slot(**self.slot_values())
        for changes in ({"room_id": self.other_room.pk}, {"provider_id": self.other_provider.pk}):
            with self.subTest(changes=changes), self.assertRaisesMessage(ValidationError, "overlapping availability"):
                save_slot(**self.slot_values(**changes))
        self.assertIsNotNone(save_slot(**self.slot_values(
            start_time=self.end, end_time=self.end + timedelta(minutes=15),
        )).pk)
        closed = save_slot(**self.slot_values(provider_id=self.other_provider.pk, is_active=False))
        with self.assertRaisesMessage(ValidationError, "overlapping availability"):
            save_slot(**self.slot_values(slot_id=closed.pk, provider_id=self.other_provider.pk))
        closed.refresh_from_db()
        self.assertFalse(closed.is_active)
        self.assertTrue(Slot.objects.get(pk=first.pk).is_active)

    @skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL range exclusion constraints")
    def test_database_independently_rejects_provider_and_room_overlaps(self):
        for provider, room, constraint in (
            (self.provider, self.other_room, "slot_no_provider_overlap"),
            (self.other_provider, self.slot.room, "slot_no_room_overlap"),
        ):
            with self.subTest(constraint=constraint):
                with self.assertRaises(IntegrityError) as failure, transaction.atomic():
                    Slot.objects.bulk_create([Slot(
                        provider=provider, room=room, start_time=self.slot.start_time + timedelta(minutes=1),
                        end_time=self.slot.end_time, is_active=True,
                    )])
                self.assertEqual(failure.exception.__cause__.diag.constraint_name, constraint)

    def test_future_time_and_positive_duration_are_enforced(self):
        old = timezone.now() - timedelta(minutes=1)
        with self.assertRaisesMessage(ValidationError, "Start time must be in the future"):
            save_slot(**self.slot_values(start_time=old))
        with self.assertRaisesMessage(ValidationError, "Slot must end after it starts"):
            save_slot(**self.slot_values(end_time=self.start))
        self.assertEqual(Slot.objects.count(), 1)

    def test_resources_are_rechecked_and_existing_ineligible_slot_can_be_closed(self):
        slot = save_slot(**self.slot_values())
        ClinicRoom.objects.filter(pk=self.other_room.pk).update(is_active=False)
        with self.assertRaisesMessage(ValidationError, "Choose an active clinic room"):
            save_slot(**self.slot_values(room_id=self.other_room.pk, is_active=False))
        User.objects.filter(pk=self.provider.pk).update(account_status=User.AccountStatus.SUSPENDED)
        with self.assertRaisesMessage(ValidationError, "Choose an active provider"):
            save_slot(**self.slot_values(start_time=self.end, end_time=self.end + timedelta(minutes=15)))
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("availability:list")), "Unavailable")
        url = reverse("availability:edit", args=[slot.pk])
        self.assertRedirects(self.client.post(url, self.post_data(slot, is_active="")), reverse("availability:list"))
        slot.refresh_from_db()
        self.assertFalse(slot.is_active)
        with self.assertRaisesMessage(ValidationError, "Choose an active provider"):
            save_slot(**self.slot_values(slot_id=slot.pk))

    def test_stale_form_does_not_overwrite_an_edit(self):
        slot = save_slot(**self.slot_values())
        old_form = self.post_data(slot, room=self.other_room.pk)
        save_slot(**self.slot_values(slot_id=slot.pk, is_active=False))
        self.client.force_login(self.admin)
        response = self.client.post(reverse("availability:edit", args=[slot.pk]), old_form)
        self.assertContains(response, "This slot changed.")
        slot.refresh_from_db()
        self.assertFalse(slot.is_active)
        self.assertEqual(slot.room_id, self.slot.room_id)
        self.assertEqual(AuditLog.objects.filter(target_table="slot", target_record_id=slot.pk).count(), 2)

    def test_booked_slot_is_read_only_and_canceled_history_preserves_schedule(self):
        slot = save_slot(**self.slot_values())
        visit = book_appointment(actor=self.patient.patient, patient_id=self.patient.pk,
            slot_id=slot.pk, reason_for_visit="Fictional booked slot")
        self.client.force_login(self.admin)
        url = reverse("availability:edit", args=[slot.pk])
        self.assertContains(self.client.get(url), "A booking or linked visit protects this slot")
        self.assertEqual(self.client.post(url, self.post_data(slot, is_active="")).status_code, 409)
        with self.assertRaisesMessage(ValidationError, "protects this slot"):
            save_slot(**self.slot_values(slot_id=slot.pk, is_active=False))
        cancel_appointment(actor=self.patient.patient, appointment_id=visit.pk)
        with self.assertRaisesMessage(ValidationError, "Appointment history protects"):
            save_slot(**self.slot_values(slot_id=slot.pk, room_id=self.other_room.pk))
        self.assertContains(self.client.get(url), "You can change whether this future slot is open.")
        # A forged room/time is ignored by the disabled scheduling fields.
        response = self.client.post(url, self.post_data(slot, room=self.other_room.pk, is_active=""))
        self.assertRedirects(response, reverse("availability:list"))
        slot.refresh_from_db()
        visit.refresh_from_db()
        self.assertEqual(visit.status, Appointment.Status.CANCELED)
        self.assertEqual(slot.schedule, (self.provider.pk, self.slot.room_id, self.start, self.end))
        self.assertFalse(slot.is_active)

    def test_past_and_unassigned_legacy_slots_have_deliberate_paths(self):
        past = Slot.objects.create(
            provider=self.provider, start_time=self.start - timedelta(days=5), end_time=self.end - timedelta(days=5),
        )
        legacy = Slot.objects.create(provider=self.provider, start_time=self.start, end_time=self.end)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("availability:list")), "Room unverified")
        past_url = reverse("availability:edit", args=[past.pk])
        self.assertContains(self.client.get(past_url), "This slot has already started.")
        self.assertEqual(self.client.post(past_url, self.post_data(past)).status_code, 409)
        self.assertRedirects(self.client.post(reverse("availability:edit", args=[legacy.pk]),
            self.post_data(legacy, room=self.slot.room_id)), reverse("availability:list"))
        legacy.refresh_from_db()
        self.assertEqual(legacy.room_id, self.slot.room_id)
        self.assertTrue(legacy.is_active)


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class AvailabilityConcurrencyTests(TransactionTestCase):
    # Allow the disposable test database flush to cascade through archived FKs.
    available_apps = settings.INSTALLED_APPS

    def test_concurrent_providers_cannot_allocate_the_same_room(self):
        admin, _, first, existing_slot, _ = clinic_data()
        other_user = User.objects.create_user("TEST-SECOND", "second@example.invalid", user_type=User.UserType.PROVIDER)
        second = Provider.objects.create(provider=other_user, provider_type=Provider.Type.PHYSICIAN, is_active=True)
        starts = existing_slot.end_time + timedelta(minutes=15)
        room_id = existing_slot.room_id
        gate = Barrier(2, timeout=10)

        def schedule(provider_id):
            close_old_connections()
            try:
                gate.wait()
                save_slot(actor=admin, provider_id=provider_id, room_id=room_id,
                    start_time=starts, end_time=starts + timedelta(minutes=30), is_active=True)
                return "created"
            except ValidationError as error:
                self.assertIn("overlapping availability", str(error))
                return "conflict"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(schedule, [first.pk, second.pk], timeout=20))
        self.assertCountEqual(outcomes, ["created", "conflict"])
        self.assertEqual(Slot.objects.filter(room_id=room_id, start_time=starts, is_active=True).count(), 1)
