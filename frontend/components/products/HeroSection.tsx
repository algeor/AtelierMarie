import Link from "next/link";
import { Button } from "@/components/ui/Button";

export function HeroSection() {
  return (
    <section
      className="w-full py-24 md:py-32 lg:py-40 px-4 sm:px-6 lg:px-8 flex flex-col items-center text-center bg-brand-gradient"
    >
      <h1 className="font-heading text-4xl md:text-5xl lg:text-6xl text-charcoal max-w-3xl">
        Luxury Handcrafted Candles
      </h1>
      <p className="mt-6 text-lg md:text-xl text-soft-brown max-w-2xl">
        Each candle is lovingly made by hand, using the finest natural
        ingredients to bring warmth and elegance to your home.
      </p>
      <Link href="/products" className="mt-10">
        <Button size="lg">Shop Collection</Button>
      </Link>
    </section>
  );
}
