import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ContactForm } from "@/components/contact/ContactForm";
import { renderWithIntl } from "@/__tests__/test-utils";
import { ApiError } from "@/lib/api-client";

const submitContactMock = vi.fn();

vi.mock("@/lib/api", () => ({
  submitContact: (...args: unknown[]) => submitContactMock(...args),
}));

describe("ContactForm", () => {
  beforeEach(() => {
    submitContactMock.mockReset();
  });

  it("shows required validation errors", async () => {
    renderWithIntl(<ContactForm />);

    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText("Name is required")).toBeInTheDocument();
    expect(screen.getByText("Email is required")).toBeInTheDocument();
    expect(screen.getByText("Message is required")).toBeInTheDocument();
    expect(submitContactMock).not.toHaveBeenCalled();
  });

  it("validates email format", async () => {
    renderWithIntl(<ContactForm />);

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "Mira" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "bad-email" } });
    fireEvent.change(screen.getByLabelText(/message/i), { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText("Please enter a valid email address")).toBeInTheDocument();
    expect(submitContactMock).not.toHaveBeenCalled();
  });

  it("submits valid data and clears the form", async () => {
    submitContactMock.mockResolvedValue({ status: "received", message_id: 12 });
    renderWithIntl(<ContactForm />);

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "Mira" } });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "mira@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: "Do you make custom candles?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => expect(submitContactMock).toHaveBeenCalledTimes(1));
    expect(submitContactMock).toHaveBeenCalledWith({
      name: "Mira",
      email: "mira@example.com",
      message: "Do you make custom candles?",
      locale: "en",
      website: "",
    });
    expect(await screen.findByText("Thank you. We will get back to you soon.")).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toHaveValue("");
    expect(screen.getByLabelText(/email/i)).toHaveValue("");
    expect(screen.getByLabelText(/message/i)).toHaveValue("");
  });

  it("preserves entered data on backend error", async () => {
    submitContactMock.mockRejectedValue(
      new ApiError({ error: { code: "RATE_LIMITED", message: "Too many", details: null } })
    );
    renderWithIntl(<ContactForm />);

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "Mira" } });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "mira@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/message/i), { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText("Too many requests. Please wait a moment.")).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toHaveValue("Mira");
    expect(screen.getByLabelText(/email/i)).toHaveValue("mira@example.com");
    expect(screen.getByLabelText(/message/i)).toHaveValue("Hello");
  });
});
