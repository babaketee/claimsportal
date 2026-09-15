"use client";

import { useState } from "react";
import clsx from "clsx";

export function Tabs({
  tabs,
}: {
  tabs: { label: string; content: React.ReactNode }[];
}) {
  const [active, setActive] = useState(0);
  return (
    <div>
      <div className="scrollbar-none -mx-1 mb-5 flex gap-1 overflow-x-auto border-b border-black/10 px-1">
        {tabs.map((t, i) => (
          <button
            key={t.label}
            onClick={() => setActive(i)}
            className={clsx(
              "shrink-0 whitespace-nowrap border-b-[3px] px-3 py-2.5 text-sm font-semibold transition-colors",
              active === i
                ? "border-brand-red text-brand-red"
                : "border-transparent text-black/50 hover:text-brand-ink"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="animate-fade-in">{tabs[active]?.content}</div>
    </div>
  );
}
