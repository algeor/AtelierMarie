import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FaqAccordion, parseFaqAnswer } from "@/components/faq/FaqAccordion";

const FIRST_SECTION = [
  { id: 1, question: "First question", answer: "First answer" },
  { id: 2, question: "Second question", answer: "Second answer" },
];

const SECOND_SECTION = [
  { id: 3, question: "Third question", answer: "Third answer" },
  { id: 4, question: "Fourth question", answer: "Fourth answer" },
];

describe("FaqAccordion", () => {
  it("keeps one item open per section while sections stay independent", () => {
    render(
      <>
        <FaqAccordion items={FIRST_SECTION} />
        <FaqAccordion items={SECOND_SECTION} />
      </>
    );

    expect(screen.getByRole("button", { name: /First question/ })).toHaveAttribute(
      "aria-expanded",
      "true"
    );
    expect(screen.getByRole("button", { name: /Third question/ })).toHaveAttribute(
      "aria-expanded",
      "true"
    );

    fireEvent.click(screen.getByRole("button", { name: /Second question/ }));

    expect(screen.getByRole("button", { name: /First question/ })).toHaveAttribute(
      "aria-expanded",
      "false"
    );
    expect(screen.getByRole("button", { name: /Second question/ })).toHaveAttribute(
      "aria-expanded",
      "true"
    );
    expect(screen.getByRole("button", { name: /Third question/ })).toHaveAttribute(
      "aria-expanded",
      "true"
    );
  });

  it("renders bullet markers as list items", () => {
    render(
      <FaqAccordion
        items={[{ id: 1, question: "Safety", answer: "Intro\n\n* First\n- Second" }]}
      />
    );

    expect(screen.getByText("Intro")).toBeInTheDocument();
    expect(screen.getByText("First").tagName).toBe("LI");
    expect(screen.getByText("Second").tagName).toBe("LI");
  });

  it("renders relative markdown links in answers", () => {
    render(
      <FaqAccordion
        items={[
          {
            id: 1,
            question: "Returns",
            answer:
              "Read the [Terms returns section](/en/terms#returns) before sending a parcel back.",
          },
        ]}
      />
    );

    expect(screen.getByRole("link", { name: "Terms returns section" })).toHaveAttribute(
      "href",
      "/en/terms#returns"
    );
  });

  it("parses paragraphs and bullet groups", () => {
    expect(parseFaqAnswer("A line\ncontinued\n\n* One\n* Two")).toEqual([
      { type: "paragraph", text: "A line continued" },
      { type: "list", items: ["One", "Two"] },
    ]);
  });
});
