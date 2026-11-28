import { HeartPulse, Smile, Stethoscope } from 'lucide-react'
import type { Provider } from '../../data/types'
import physicianImg from './assets/service-physician.jpg'
import nurseImg from './assets/service-nurse.jpg'
import dentalImg from './assets/service-dental.jpg'
import maraImg from './assets/provider-mara-villareal.jpg'
import joelImg from './assets/provider-joel-macaraeg.jpg'

const careImage = { physician: physicianImg, nurse: nurseImg, dentist: dentalImg }

const bookingPhotos = { 'mara-villareal': maraImg, 'joel-macaraeg': joelImg }

export function bookingImage(provider: Provider) {
  const portrait = provider.booking_photo && bookingPhotos[provider.booking_photo]
  return portrait || careImage[provider.provider_type as keyof typeof careImage]
}

export const careIcon = { physician: Stethoscope, nurse: HeartPulse, dentist: Smile }
