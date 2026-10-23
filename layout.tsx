import type { Metadata } from "next";
export const metadata: Metadata = { title: "ترب‌یار | دستیار خرید", description: "جست‌وجو و مقایسه قیمت فروشگاه‌ها" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="fa" dir="rtl"><body>{children}</body></html>;
}
