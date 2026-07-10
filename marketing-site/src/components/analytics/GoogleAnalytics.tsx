/**
 * Google Analytics 4 (production only).
 *
 * Set your Measurement ID in the deployment environment:
 *   NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
 *
 * Find it in Google Analytics → Admin → Data Streams → your web stream.
 * Leave unset during local development — analytics will not load.
 */

import { GoogleAnalytics as NextGoogleAnalytics } from "@next/third-parties/google";

const measurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID?.trim();

export function GoogleAnalytics() {
  if (process.env.NODE_ENV !== "production" || !measurementId) {
    return null;
  }

  return <NextGoogleAnalytics gaId={measurementId} />;
}
