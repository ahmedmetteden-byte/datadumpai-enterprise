import { softwareApplicationJsonLd } from "@/lib/metadata";

type JsonLdData = Record<string, unknown> | Record<string, unknown>[];

export function JsonLd({ data }: { data: JsonLdData }) {
  const items = Array.isArray(data) ? data : [data];

  return (
    <>
      {items.map((item, index) => (
        <script
          key={index}
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(item) }}
        />
      ))}
    </>
  );
}

export function SoftwareApplicationSchema() {
  return <JsonLd data={softwareApplicationJsonLd()} />;
}
