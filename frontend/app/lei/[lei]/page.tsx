import { fetchLei } from "@/lib/api";
import { notFound } from "next/navigation";
import Link from "next/link";
import { clsx } from "clsx";
import { jurisdictionName } from "@/lib/jurisdictions";

export const dynamic = "force-dynamic";

function Field({ label, value, mono = false }: { label: string; value?: string | null; mono?: boolean }) {
  if (!value) return null;
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-widest text-muted">{label}</span>
      <span className={clsx("text-sm text-white", mono && "font-mono break-all")}>{value}</span>
    </div>
  );
}

function AddressBlock({ label, addr }: {
  label: string;
  addr?: { lines?: string[]; city?: string; region?: string; country?: string; postal_code?: string } | null;
}) {
  if (!addr) return null;
  const parts = [
    ...(addr.lines ?? []),
    [addr.city, addr.postal_code].filter(Boolean).join(" "),
    addr.region,
    addr.country,
  ].filter(Boolean) as string[];
  if (!parts.length) return null;
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-widest text-muted">{label}</span>
      <div className="text-sm text-white leading-relaxed">
        {parts.map((p, i) => <div key={i}>{p}</div>)}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status?: string | null }) {
  const active = status === "ACTIVE";
  return (
    <span className={clsx(
      "shrink-0 text-xs font-medium px-2 py-1 rounded uppercase tracking-wider",
      active
        ? "bg-teal/10 text-teal border border-teal/20"
        : "bg-danger/10 text-danger border border-danger/20"
    )}>
      {status || "—"}
    </span>
  );
}

function fmtDate(iso?: string | null) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

export default async function LeiDetailPage({ params }: { params: Promise<{ lei: string }> }) {
  const { lei } = await params;

  let record: Awaited<ReturnType<typeof fetchLei>>;
  try {
    record = await fetchLei(lei.toUpperCase());
  } catch (err: unknown) {
    const status = (err as { status?: number }).status;
    if (status === 404) notFound();
    // Surface backend errors so they're visible in the browser
    throw err;
  }

  const legalAddrSameAsHq =
    JSON.stringify(record.legal_address) === JSON.stringify(record.hq_address);

  return (
    <div className="space-y-5 max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-white leading-tight">
            {record.legal_name || "Unknown Entity"}
          </h1>
          {record.other_names?.length > 0 && (
            <p className="text-xs text-muted mt-0.5">
              Also known as: {record.other_names.join(", ")}
            </p>
          )}
          <p className="text-xs text-muted font-mono mt-1 break-all">{record.lei}</p>
        </div>
        <StatusBadge status={record.entity_status} />
      </div>

      {/* Entity information */}
      <div className="bg-card border border-edge rounded-lg p-5">
        <h2 className="text-xs uppercase tracking-widest text-muted mb-4">Entity Information</h2>
        <div className="grid grid-cols-2 gap-x-8 gap-y-4 lg:grid-cols-3">
          <Field label="Legal Name" value={record.legal_name} />
          <Field label="Jurisdiction" value={record.jurisdiction ? jurisdictionName(record.jurisdiction) : null} />
          <Field label="Entity Category" value={record.entity_category} />
          <Field label="Entity Status" value={record.entity_status} />
          <Field label="Registration Status" value={record.registration_status} />
          {record.legal_form && <Field label="Legal Form" value={record.legal_form} />}
          {record.registered_as && <Field label="Company Reg. No." value={record.registered_as} mono />}
        </div>
      </div>

      {/* Addresses */}
      {(record.legal_address || record.hq_address) && (
        <div className="bg-card border border-edge rounded-lg p-5">
          <h2 className="text-xs uppercase tracking-widest text-muted mb-4">Addresses</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <AddressBlock label="Legal Address" addr={record.legal_address} />
            {!legalAddrSameAsHq && (
              <AddressBlock label="Headquarters Address" addr={record.hq_address} />
            )}
          </div>
        </div>
      )}

      {/* Registration dates */}
      <div className="bg-card border border-edge rounded-lg p-5">
        <h2 className="text-xs uppercase tracking-widest text-muted mb-4">Registration Dates</h2>
        <div className="grid grid-cols-2 gap-x-8 gap-y-4 lg:grid-cols-3">
          <Field label="Initial Registration" value={fmtDate(record.initial_registration_date)} />
          <Field label="Last Updated" value={fmtDate(record.last_update_date)} />
          <Field label="Next Renewal" value={fmtDate(record.next_renewal_date)} />
          {record.corroboration_level && (
            <Field label="Corroboration Level" value={record.corroboration_level} />
          )}
          {record.validated_at && (
            <Field label="Validated At" value={record.validated_at} />
          )}
        </div>
      </div>

      {/* Managing LOU */}
      <div className="bg-card border border-edge rounded-lg p-5">
        <h2 className="text-xs uppercase tracking-widest text-muted mb-4">Managing LOU</h2>
        {record.managing_lou ? (
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium text-white">
                {record.managing_lou_name || "Unknown LOU"}
              </p>
              <p className="text-xs text-muted font-mono mt-0.5 break-all">{record.managing_lou}</p>
            </div>
            <Link
              href={`/lous/${record.managing_lou}`}
              className="shrink-0 text-xs text-teal hover:text-teal-dim border border-teal/30 rounded px-3 py-1.5 transition-colors"
            >
              View LOU →
            </Link>
          </div>
        ) : (
          <p className="text-sm text-muted">No managing LOU recorded</p>
        )}
      </div>

      <Link href="/search" className="inline-block text-xs text-muted hover:text-white transition-colors">
        ← Back to search
      </Link>
    </div>
  );
}
