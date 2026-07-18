import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ReasonModal from "../ReasonModal";

function setup(props: Partial<React.ComponentProps<typeof ReasonModal>> = {}) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(
    <ReasonModal
      open
      title="Void invoice line"
      description="The line stays on record, marked void."
      onConfirm={onConfirm}
      onCancel={onCancel}
      {...props}
    />,
  );
  return { onConfirm, onCancel };
}

describe("ReasonModal", () => {
  it("refuses to confirm without a reason", async () => {
    const { onConfirm } = setup();
    const confirm = screen.getByRole("button", { name: "Confirm" });
    expect(confirm).toBeDisabled();
    await userEvent.click(confirm).catch(() => {});
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("flags a whitespace-only reason as invalid on blur", async () => {
    setup();
    const field = screen.getByLabelText("Reason (required)");
    await userEvent.type(field, "   ");
    await userEvent.tab();
    expect(screen.getByText(/reason is required for audit/i)).toBeInTheDocument();
  });

  it("confirms with the trimmed reason", async () => {
    const { onConfirm } = setup();
    await userEvent.type(screen.getByLabelText("Reason (required)"), "  keyed wrong  ");
    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(onConfirm).toHaveBeenCalledWith("keyed wrong");
  });

  it("cancel and Escape both close without confirming", async () => {
    const { onConfirm, onCancel } = setup();
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledOnce();
    await userEvent.keyboard("{Escape}");
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("renders the audit wording", () => {
    setup();
    expect(screen.getByText("The line stays on record, marked void.")).toBeInTheDocument();
  });
});
