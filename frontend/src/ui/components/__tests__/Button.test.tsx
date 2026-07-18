import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Button from "../Button";

describe("Button", () => {
  it("fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("is disabled and unclickable while loading", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Save
      </Button>,
    );
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    await userEvent.click(button).catch(() => {});
    expect(onClick).not.toHaveBeenCalled();
  });

  it("uses the brand CSS variable for the primary variant", () => {
    render(<Button variant="primary">Go</Button>);
    expect(screen.getByRole("button").style.backgroundColor).toContain("--hms-primary");
  });
});
