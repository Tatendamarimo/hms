import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import EmptyState from "../EmptyState";
import ErrorState from "../ErrorState";
import LoadingState from "../LoadingState";

describe("screen states", () => {
  it("LoadingState shows its message", () => {
    render(<LoadingState message="Loading patient…" />);
    expect(screen.getByText("Loading patient…")).toBeInTheDocument();
  });

  it("EmptyState shows its title", () => {
    render(<EmptyState title="No records found" />);
    expect(screen.getByText("No records found")).toBeInTheDocument();
  });

  it("ErrorState offers retry when a handler is given", async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Unable to load data." onRetry={onRetry} />);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("ErrorState hides retry without a handler", () => {
    render(<ErrorState />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
