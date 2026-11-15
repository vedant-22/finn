// Alerts on this phone: real system notifications, with the investor's permission.
// FINN's data is a snapshot built after the close, so there is no background push. When the app opens on a newer
// snapshot, anything that crossed a line since the last visit is raised as a notification; turning alerts on shows
// the top item at once, so the investor sees what one looks like.
import { load, save } from './storage'
export const canAlert = () => typeof window !== 'undefined' && 'Notification' in window && 'serviceWorker' in navigator
export const alertsOn = () => canAlert() && Notification.permission === 'granted' && load('alerts') === 'on'
export const alertsBlocked = () => canAlert() && Notification.permission === 'denied'

export interface Alert { key: string; title: string; body: string }

async function show(a: Alert) {
  const opts = { body: a.body, tag: a.key, icon: '/icon-192.png', badge: '/icon-192.png', data: { url: '/#/read' } }
  const reg = await navigator.serviceWorker.getRegistration()
  if (reg) await reg.showNotification(a.title, opts)
  else new Notification(a.title, opts)
}

export async function enableAlerts(first?: Alert): Promise<'on' | 'denied' | 'unsupported'> {
  if (!canAlert()) return 'unsupported'
  const p = Notification.permission === 'granted' ? 'granted' : await Notification.requestPermission()
  if (p !== 'granted') return 'denied'
  save('alerts', 'on')
  if (first) await show(first).catch(() => {})
  return 'on'
}
export const disableAlerts = () => { save('alerts', 'off') }

// At most three at once: past that, the brief itself is the notification
export function raise(alerts: Alert[]) {
  if (!alertsOn()) return
  alerts.slice(0, 3).forEach(a => { show(a).catch(() => {}) })
}
