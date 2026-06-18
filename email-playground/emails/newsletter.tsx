import {
  Body,
  Column,
  Container,
  Head,
  Heading,
  Hr,
  Html,
  Link,
  Row,
  Section,
  Tailwind,
  Text,
} from "@react-email/components";
import * as React from "react";

const MEDIAPULSE_URL = "https://mediapulse.hyperjump.tech";
const HYPERJUMP_URL = "https://hyperjump.tech";
const QUICK_HITS = "Quick Hits";

const WAVE_DIVIDER =
  "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='40'%20height='10'%20viewBox='0%200%2040%2010'%3E%3Cpath%20d='M0%205%20Q10%200%2020%205%20T40%205'%20fill='none'%20stroke='%23d1d5db'%20stroke-width='2'/%3E%3C/svg%3E";

const TOKEN_ITEM: NewsletterItem = {
  summary: "{{item_summary}}",
  title: "{{item_title}}",
  url: "{{item_url}}",
};

export interface NewsletterItem {
  summary: string;
  title: string;
  url: string;
}

export interface NewsletterSection {
  name: string;
  items: NewsletterItem[];
}

export interface NewsletterEmailProps {
  title: string;
  summary?: string;
  sections: NewsletterSection[];
  subjectSymbol?: string;
  unsubscribeUrl?: string;
  templateMode?: boolean;
}

function footerNote(symbol?: string): string {
  const trimmed = (symbol ?? "").trim();

  return trimmed
    ? `You are receiving this because you subscribed to ${trimmed} updates.`
    : "You are receiving this because you subscribed to updates.";
}

function Region({
  name,
  templateMode,
  children,
}: {
  name: string;
  templateMode: boolean;
  children: React.ReactNode;
}) {
  if (!templateMode) {
    return <>{children}</>;
  }

  return (
    <>
      {`[[#${name}]]`}
      {children}
      {`[[/${name}]]`}
    </>
  );
}

function WavyDivider() {
  return (
    <Section className="my-6">
      <Row>
        <Column
          style={{
            height: "10px",
            fontSize: "0",
            lineHeight: "10px",
            backgroundImage: `url("${WAVE_DIVIDER}")`,
            backgroundRepeat: "repeat-x",
            backgroundPosition: "center",
          }}
        >
          &nbsp;
        </Column>
      </Row>
    </Section>
  );
}

function ItemList({
  items,
  templateMode,
}: {
  items: NewsletterItem[];
  templateMode: boolean;
}) {
  return (
    <>
      {items.map((item, index) => (
        <Region key={index} name="item" templateMode={templateMode}>
          {index > 0 || templateMode ? (
            <Region name="itemsep" templateMode={templateMode}>
              <Hr className="my-4 border-0 border-t border-gray-200" />
            </Region>
          ) : null}

          <Text className="m-0 text-base leading-relaxed text-gray-700">
            {item.summary}
          </Text>

          {item.url ? (
            <Region name="readlink" templateMode={templateMode}>
              <Text className="mb-0 mt-2 text-sm leading-normal">
                <Link href={item.url} className="text-blue-600 underline">
                  {`Read: ${item.title || "the source"}`}
                </Link>
              </Text>
            </Region>
          ) : null}
        </Region>
      ))}
    </>
  );
}

function SectionBlock({
  name,
  items,
  isFirst,
  templateMode,
  variant,
}: {
  name: string;
  items: NewsletterItem[];
  isFirst: boolean;
  templateMode: boolean;
  variant: "standard" | "quickhits";
}) {
  const heading = (
    <Heading
      as="h2"
      className="m-0 mb-4 text-lg font-semibold leading-tight text-gray-900 max-sm:text-base"
    >
      {name}
    </Heading>
  );

  return (
    <>
      {!isFirst || templateMode ? (
        <Region name="sectionsep" templateMode={templateMode}>
          <Hr className="my-6 border-0 border-t border-gray-200" />
        </Region>
      ) : null}

      {variant === "quickhits" ? (
        <Section className="rounded-xl border-l-4 border-blue-600 bg-gray-50 px-5 py-4">
          {heading}
          <ItemList items={items} templateMode={templateMode} />
        </Section>
      ) : (
        <Section>
          {heading}
          <ItemList items={items} templateMode={templateMode} />
        </Section>
      )}
    </>
  );
}

export function NewsletterEmail({
  title,
  summary,
  sections,
  subjectSymbol,
  unsubscribeUrl,
  templateMode = false,
}: NewsletterEmailProps) {
  const footerText = templateMode
    ? "{{footer_note}}"
    : footerNote(subjectSymbol);
  const unsubscribeLabel = templateMode
    ? "{{symbol}}"
    : subjectSymbol || "these";

  return (
    <Html>
      <Tailwind>
        <Head />
        <Body className="m-0 bg-gray-50 p-0 font-sans">
          <Container
            className="mx-auto mb-8 mt-8 max-w-[600px] border border-gray-200 bg-white px-6 py-8 max-sm:mt-0"
            style={{
              boxShadow:
                "0 1px 2px rgba(0,0,0,0.12), 0 8px 0 -4px #f3f4f6, 0 8px 1px -3px rgba(0,0,0,0.12), 0 16px 0 -8px #f3f4f6, 0 16px 1px -7px rgba(0,0,0,0.12)",
            }}
          >
            <Heading className="m-0 text-2xl font-semibold leading-tight text-gray-900 max-sm:text-xl">
              {title}
            </Heading>

            {summary ? (
              <Region name="standfirst" templateMode={templateMode}>
                <Text className="mb-0 mt-4 text-lg leading-relaxed text-gray-700 max-sm:text-base">
                  {summary}
                </Text>
              </Region>
            ) : null}

            <WavyDivider />

            <Region name="sections" templateMode={templateMode}>
              {templateMode ? (
                <>
                  <Region name="section" templateMode>
                    <SectionBlock
                      name="{{section_name}}"
                      items={[TOKEN_ITEM]}
                      isFirst={false}
                      templateMode
                      variant="standard"
                    />
                  </Region>
                  <Region name="quickhits" templateMode>
                    <SectionBlock
                      name="{{section_name}}"
                      items={[TOKEN_ITEM]}
                      isFirst={false}
                      templateMode
                      variant="quickhits"
                    />
                  </Region>
                </>
              ) : (
                sections.map((section, index) => (
                  <SectionBlock
                    key={section.name}
                    name={section.name}
                    items={section.items}
                    isFirst={index === 0}
                    templateMode={false}
                    variant={
                      section.name === QUICK_HITS ? "quickhits" : "standard"
                    }
                  />
                ))
              )}
            </Region>
          </Container>

          <Container className="mx-auto max-w-[600px] px-6 py-6 text-center max-sm:py-4">
            <Text
              className="text-center text-sm leading-normal text-gray-600 max-sm:text-xs"
              style={{ margin: 0 }}
            >
              Brought to you by{" "}
              <Link href={MEDIAPULSE_URL} className="text-blue-600 underline">
                MediaPulse
              </Link>
              , a product of{" "}
              <Link href={HYPERJUMP_URL} className="text-blue-600 underline">
                Hyperjump
              </Link>
              .
            </Text>

            <Text
              className="text-center text-xs leading-normal text-gray-500"
              style={{ margin: "6px 0 0" }}
            >
              {footerText}
            </Text>

            {unsubscribeUrl ? (
              <Region name="unsubscribe" templateMode={templateMode}>
                <Text
                  className="text-center text-xs text-gray-400"
                  style={{ margin: "6px 0 0" }}
                >
                  <Link
                    href={unsubscribeUrl}
                    className="text-blue-600 underline"
                  >
                    {`Unsubscribe from ${unsubscribeLabel} updates`}
                  </Link>
                </Text>
              </Region>
            ) : null}
          </Container>
        </Body>
      </Tailwind>
    </Html>
  );
}

export const templateProps: NewsletterEmailProps = {
  title: "{{title}}",
  summary: "{{summary}}",
  unsubscribeUrl: "{{unsubscribe_url}}",
  templateMode: true,
  sections: [{ name: "{{section_name}}", items: [TOKEN_ITEM] }],
};

NewsletterEmail.PreviewProps = {
  title: "ACME Pulse: A Big Week for the Robotics Desk",
  summary:
    "A rival cut prices, ACME signed three logistics partners, regulators opened a routine review, the team previewed on-device vision, and the developer conference sold out. Here is the full briefing.",
  subjectSymbol: "ACME",
  unsubscribeUrl: "https://mediapulse.hyperjump.tech/unsubscribe?token=sample",
  sections: [
    {
      name: "Competitive Landscape",
      items: [
        {
          summary:
            "Rival maker Botworks cut prices on its mid-range arm by 15 percent, undercutting ACME on the warehouse tier where the two compete most directly.",
          title: "Botworks price cut",
          url: "https://example.com/botworks-pricing",
        },
        {
          summary:
            "An independent benchmark put ACME's pick-and-place accuracy ahead of two larger competitors, though it trailed on cycle time.",
          title: "Benchmark results",
          url: "https://example.com/robotics-benchmark",
        },
      ],
    },
    {
      name: "Deals & Movements",
      items: [
        {
          summary:
            "ACME signed three new logistics partners for its warehouse arm, expanding the rollout to a second continent.",
          title: "ACME partner expansion",
          url: "https://example.com/acme-partners",
        },
        {
          summary:
            "A former ACME vice president of engineering joined a rival, the second senior departure this quarter.",
          title: "Leadership move",
          url: "https://example.com/acme-departure",
        },
      ],
    },
    {
      name: "Regulatory & Policy Watch",
      items: [
        {
          summary:
            "A regional safety body opened a routine review of autonomous warehouse equipment. No findings have been published.",
          title: "Safety review notice",
          url: "https://example.com/acme-review",
        },
      ],
    },
    {
      name: "Disruptors & Tech",
      items: [
        {
          summary:
            "ACME previewed an on-device vision model it says will let arms re-plan grasps without a cloud round trip, due in the next firmware cycle.",
          title: "On-device vision preview",
          url: "https://example.com/acme-vision",
        },
        {
          summary:
            "A seed-stage startup demoed a cheaper tactile sensor that could pressure incumbents if it reaches volume production.",
          title: "Tactile sensor demo",
          url: "https://example.com/tactile-startup",
        },
      ],
    },
    {
      name: "Quick Hits",
      items: [
        {
          summary:
            "ACME's developer conference sold out in under an hour, with a waitlist now open.",
          title: "Conference sells out",
          url: "https://example.com/acme-devcon",
        },
        {
          summary:
            "The company published a teardown of last month's outage and the mitigations it has since shipped.",
          title: "Outage postmortem",
          url: "https://example.com/acme-postmortem",
        },
      ],
    },
  ],
} satisfies NewsletterEmailProps;

export default NewsletterEmail;
