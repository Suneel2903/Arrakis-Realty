import { db } from "@/lib/db";
import { health } from "@/lib/health";

export async function GET() {
  return health(() => db()`select 1`);
}
