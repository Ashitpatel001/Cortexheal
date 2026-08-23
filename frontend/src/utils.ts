import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { formatDistanceToNow, parseISO } from "date-fns"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function relativeTime(timestamp: string) {
  try {
    return formatDistanceToNow(parseISO(timestamp), { addSuffix: true })
  } catch (e) {
    return timestamp
  }
}
