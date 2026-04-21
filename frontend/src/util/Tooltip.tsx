import React, { useState } from "react";

export default function Tooltip({
  text,
  children,
  side = "bottom",
}: {
  text: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "bottom" | "right";
}) {
  const [open, setOpen] = useState(false);
  return (
    <span
      className="tt-wrap"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && <span className={`tt tt-${side}`}>{text}</span>}
    </span>
  );
}
