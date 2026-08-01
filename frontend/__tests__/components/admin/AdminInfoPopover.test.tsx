import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminInfoPopover } from "@/components/admin/AdminInfoPopover";
import { renderWithIntl } from "../../test-utils";

afterEach(() => {
  vi.useRealTimers();
});

describe("AdminInfoPopover", () => {
  it("opens on click and closes with the close button", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AdminInfoPopover content="This explains the field." />);

    await user.click(screen.getByRole("button", { name: "More information" }));
    const dialog = screen.getByRole("dialog", { name: "More information" });
    expect(dialog).toHaveTextContent("This explains the field.");

    await user.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog", { name: "More information" })).not.toBeInTheDocument();
  });

  it("opens on hover and keyboard focus", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AdminInfoPopover content="Hover or focus help." />);

    const trigger = screen.getByRole("button", { name: "More information" });
    act(() => {
      fireEvent.mouseEnter(trigger.parentElement as HTMLElement);
    });
    expect(screen.getByRole("dialog", { name: "More information" })).toHaveTextContent("Hover or focus help.");

    await user.click(within(screen.getByRole("dialog", { name: "More information" })).getByRole("button", { name: "Close" }));
    act(() => {
      fireEvent.focus(trigger);
    });
    expect(screen.getByRole("dialog", { name: "More information" })).toHaveTextContent("Hover or focus help.");
  });

  it("closes on outside click and Escape", async () => {
    const user = userEvent.setup();
    renderWithIntl(
      <div>
        <AdminInfoPopover content="Extra help." />
        <button type="button">Outside</button>
      </div>
    );

    const trigger = screen.getByRole("button", { name: "More information" });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "More information" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Outside" }));
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "More information" })).not.toBeInTheDocument();
    });

    await user.click(trigger);
    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "More information" })).not.toBeInTheDocument();
    });
  });

  it("closes after the mouse leaves the popover area", () => {
    vi.useFakeTimers();
    renderWithIntl(<AdminInfoPopover content="Desktop hover close." />);

    const trigger = screen.getByRole("button", { name: "More information" });
    fireEvent.click(trigger);
    expect(screen.getByRole("dialog", { name: "More information" })).toBeInTheDocument();

    fireEvent.mouseLeave(trigger.parentElement as HTMLElement);
    act(() => {
      vi.advanceTimersByTime(130);
    });

    expect(screen.queryByRole("dialog", { name: "More information" })).not.toBeInTheDocument();
  });
});
