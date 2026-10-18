import type { EventDetail, TicketType } from "@/shared/api/types";
import { formatMoney, isZero } from "@/shared/format";
import { StatusBadge } from "@/shared/ui/table";

function availability(t: TicketType) {
  if (typeof t.available === "number") return t.available > 0 ? `${t.available} remaining` : "None remaining";
  if (typeof t.available === "boolean") return t.available ? "Available" : "Unavailable";
  return null;
}

export function TicketCards({ event }: { event: EventDetail }) {
  if (event.ticket_types.length === 0) {
    return <p className="text-muted-foreground">Tickets aren't on sale yet.</p>;
  }
  const hasTax = event.tax_name && !isZero(event.tax_rate);
  return (
    <div>
      <ul className="grid gap-4 sm:grid-cols-2">
        {event.ticket_types.map((t) => (
          <li key={t.id} className="panel flex flex-col p-5">
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-semibold">{t.name}</h3>
              <StatusBadge status={t.sale_state} />
            </div>
            <p className="mt-2 font-display text-2xl">{isZero(t.price) ? "Free" : formatMoney(t.price, event.currency)}</p>
            {t.description && <p className="mt-2 text-sm text-muted-foreground">{t.description}</p>}
            {availability(t) && <p className="mt-auto pt-3 text-sm">{availability(t)}</p>}
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-muted-foreground">
        {hasTax && `Prices ${event.prices_include_tax ? "include" : "exclude"} ${event.tax_name} at ${Number(event.tax_rate)}%. `}
        {event.booking_fee && !isZero(event.booking_fee) && `A booking fee of ${formatMoney(event.booking_fee, event.currency)} applies. `}
        Final totals are confirmed at checkout.
      </p>
    </div>
  );
}

