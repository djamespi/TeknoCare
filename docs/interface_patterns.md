# Shared clinic interface

Clinic application pages use a navy (#002870) and yellow (#FDD108) identity.
Plus Jakarta Sans serves controls and clinical data. Bricolage Grotesque serves display headings.
The fonts and licenses live in static/fonts. The header offers role-specific primary
destinations and a searchable Services directory. Registration, booking, navigation
and the patient chart also work with JavaScript disabled.

The task-first home pages draw on the [NHS hub page pattern](https://service-manual.nhs.uk/design-system/patterns/hub-page).
The booking review uses the [GOV.UK check answers pattern](https://design-system.service.gov.uk/patterns/check-answers/).
The original sign-in image in `static/clinic-visit.jpg` depicts a fictional consultation.
It was generated with the built-in ImageGen tool using this brief.

> Editorial photograph for a university clinic portal in Cebu. A fictional Filipino university student, clearly adult, in a pale blue shirt and a nurse in navy scrubs talking across a simple clinic desk. Candid and warm, natural window light, wide architectural framing, green foliage outside louvered windows, subtle film texture. Faces in the upper middle of the frame, enough breathing room to crop as a landscape banner or tall panel. No logos or text.

The [Figma Make source](https://www.figma.com/make/lvmXXb3jU9vbkkADR9us4k/Build-TeknoCare-Clinic)
provides the React components, routes, theme and interaction layouts in
`frontend/src`. The supplied Make ZIP provides the four original photos and
favicon. Django serves the built portal at `/portal/` and redirects entry pages
there when the bundle is present. Protected Django forms remain reachable through
the portal where a workflow needs extra controls, including provider onboarding and
simulated finance confirmations. The ERD and authorization services govern both
interfaces.

The adapter uses same-origin Django session cookies and CSRF tokens. Authenticated
responses deliver role-scoped data. The reference import added 7 departments,
16 diagnoses and 12 medications to Supabase. The provider Formulary reads active
catalog entries. The catalog represents formulations available for prescribing.

Build from the Django project root using Node.js 24 or a compatible Vite runtime.

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run check
npm.cmd --prefix frontend run build
```

The build writes `static/portal`. Build before `collectstatic` when deploying.
The Make prototype authentication, sample browser database and demo reset controls
were removed. The Django templates provide the no-JavaScript clinic pages.

## Layout and forms

- Extend `templates/base.html`. Supply `title` and `content`; use `styles` for
  feature-only CSS and `main_class` for a different content width. The base owns
  the HTML/head/body, one main landmark, skip link, authenticated navigation,
  notifications, prototype footer and shared form enhancement script. Do not nest
  another main or duplicate message loops inside feature templates.
- `static/css/includes/site.css` owns light/dark color variables, navigation,
  typography, buttons, form controls, error/status notices, cards, tables and
  pagination. Feature styles should consume those variables, not reintroduce
  page-specific hardcoded light backgrounds. Old duplicate CSS/import chains and
  per-page autofocus/animation scripts have been removed.
- Use a POST form with CSRF, include `includes/form_fields.html`, and give the
  submit button `class="button"`. The shared renderer keeps Django's field-group
  labels, help/error references and invalid-state attributes. Password help comes
  from the configured validators, not a separate hardcoded rules list.
- Errors appear in a linked summary plus the relevant field. The shared deferred
  script focuses the summary after an invalid submission; it does not jump to an
  obsolete field or steal focus on a normal page visit. Forms and server-side
  validation remain usable without JavaScript.
- After a successful mutation, redirect and use Django messages. Shared messages
  render success/info as status notices and error-level messages as alerts.
  Keep credentials, health details and arbitrary user content out of messages.

## Theme scope

`apps.user_settings.context_processors.appearance` reads only the signed-in user's
saved `dark_mode` value. It never creates a settings row during a GET. Missing
settings and signed-out pages default to light. The base puts the selected theme
on the HTML element before styles load; no localStorage or client-side theme
override is used. Saving Settings applies on the redirected page and subsequent
clinic pages, including password pages and the next sign-in.

Signing out returns public login/registration to light; one user's theme must not
leak to another account. Django admin is a separate, read-only framework utility
and retains Django's own appearance controls; the clinic preference does not
override that utility. No schema change is needed for these existing preferences.

Email notifications remain a saved preference only. Help text and notices must
explicitly state that delivery is unavailable; checking the box does not configure
email, subscribe someone to a live service or enable password recovery.

## Role dashboards and data boundaries

The dashboard shows the current account's role/status, optional Patient affiliation
and optional Provider designation/clinical activation. It does not display other
accounts, clinical notes, invented operational totals or unimplemented feature
links. Existing profile, settings and password tasks work for all three roles.
Admin additionally gets Clinic setup, password assistance and a read-only account
inspection link. Clinic setup's reference/account lists are Admin-only and do not
publish patient clinical notes.
Providers see clinical activation separately from account activity, with nursing
limits made explicit. Admin/Provider secondary Patient profiles do not switch their
primary workspace or grant extra permissions.

Later feature cards must have an implemented, authorized destination and real
scoped data before being added. Hiding a card never replaces service authorization.
Step 5 links owners to their patient details and gives Admin a patient intake
directory with separate identity and affiliation forms. The display profile edits
contact phone, home address and non-clinical bio. Owners edit birth dates and
emergency contacts through the patient details page.

## Tables, empty states and pagination

The shared table styles and includes are now used by Step 4's paginated reference
lists. `includes/management_list.html` provides their shared actions, bound search
and status filters, empty state and pagination; `includes/management_form.html`
provides simple Admin forms. Keep feature models/forms/services/views in their
owning apps. Use a caption, header scopes and an accessible horizontal
scroll region for a wide table:

```html
<div class="table-scroll" role="region" aria-label="Results table" tabindex="0">
  <table>
    <caption>Results</caption>
    <thead><tr><th scope="col">Name</th><th scope="col">Status</th></tr></thead>
    <tbody>{% for row in page_obj %}<tr><td>{{ row.name }}</td><td>{{ row.status }}</td></tr>{% endfor %}</tbody>
  </table>
</div>
{% include 'includes/pagination.html' %}
```

Scope and filter the queryset on the server before passing it through Django's
Paginator; use `get_page` for invalid/out-of-range page input. Pass `page_obj` and
the normal request context. The registered `clinic_ui` tag library replaces only
the `page` parameter, preserves repeated filters and URL-encodes values. Rendered
links are escaped. First/Previous/Next/Last controls appear only where applicable;
single-page results need no pagination navigation.

For an empty list include `includes/empty_state.html`, optionally supplying
`empty_title` and `empty_message`. Those values remain escaped. Do not show an
empty clinical list as though authorization succeeded if the caller lacks access.

## Verification limits

Automated tests cover role-specific working links, own-account data, secondary
profiles, unknown affiliation, inactive/unverified providers, theme persistence
and isolation, GET read-only behavior, CSRF, escaped content, label/help/error
references and pagination boundaries/filter preservation. Palette calculations
guard the selected text/control contrast pairs; they are not a complete
accessibility certification. Actual layout, keyboard/screen-reader behavior,
browser zoom and narrow-screen appearance still require the user's manual review.
Follow [the Step 3 checklist](step_3_verification.md); do not use Computer Use or
request/capture screenshots.
