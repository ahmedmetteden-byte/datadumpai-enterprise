export async function register() {
  if (process.env.NODE_ENV !== "production") {
    return;
  }

  const { initMonitoring } = await import("@/lib/monitoring");
  await initMonitoring();
}
