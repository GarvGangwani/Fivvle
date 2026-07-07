import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type {
  ClarifyingQuestion,
  ClarifyingQuestionAnswer,
  PastClarifyingTurn,
} from "@/lib/types";
import { ClarifyingQuestionBlock } from "../ClarifyingQuestionBlock";

vi.mock("../refinement-ascent.css", () => ({}));
vi.mock("../refinement-thread.css", () => ({}));

const pendingQuestion: ClarifyingQuestion = {
  question: "What is your go-to-market motion?",
  selection_mode: "multiple",
  options: ["Product-led", "Sales-led", "Community"],
};

const pastQuestionA: ClarifyingQuestion = {
  question: "Who is your primary customer?",
  selection_mode: "multiple",
  options: ["SMB", "Enterprise", "Consumers"],
};

const pastQuestionB: ClarifyingQuestion = {
  question: "What problem are you solving?",
  selection_mode: "multiple",
  options: ["Cost", "Speed", "Quality"],
};

function makePastTurn(
  question: ClarifyingQuestion,
  answer: ClarifyingQuestionAnswer,
  messageId: string,
  globalQuestionNumber: number,
): PastClarifyingTurn {
  return {
    question,
    answer,
    answerMessageId: messageId,
    globalQuestionNumber,
  };
}

const defaultProps = {
  questions: [pendingQuestion],
  onSubmit: vi.fn(),
};

afterEach(() => {
  cleanup();
});

describe("ClarifyingQuestionBlock", () => {
  it("backward compat: no pastTurns keeps Previous disabled at first question", () => {
    const { container } = render(<ClarifyingQuestionBlock {...defaultProps} />);

    const previous = screen.getByRole("button", { name: "Previous" });
    expect(previous).toBeDisabled();
    expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument();
    expect(container).toMatchSnapshot();
  });

  it("enters past-turn mode from the first pending question", async () => {
    const user = userEvent.setup();
    const pastTurns = [
      makePastTurn(
        pastQuestionA,
        { selectedOptions: ["SMB"], otherText: "" },
        "msg-1",
        1,
      ),
    ];

    render(
      <ClarifyingQuestionBlock
        {...defaultProps}
        pastTurns={pastTurns}
        onEditPast={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Previous" }));

    expect(
      screen.getByText(
        /Editing question 1 — changes will regenerate later questions\./,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Who is your primary customer\?/)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /SMB/ })).toBeChecked();
  });

  it("navigates forward through multiple past turns", async () => {
    const user = userEvent.setup();
    const pastTurns = [
      makePastTurn(
        pastQuestionA,
        { selectedOptions: ["SMB"], otherText: "" },
        "msg-1",
        1,
      ),
      makePastTurn(
        pastQuestionB,
        { selectedOptions: ["Speed"], otherText: "" },
        "msg-2",
        2,
      ),
    ];

    render(
      <ClarifyingQuestionBlock
        {...defaultProps}
        pastTurns={pastTurns}
        onEditPast={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(screen.getByText(/Who is your primary customer\?/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText(/What problem are you solving\?/)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Speed/ })).toBeChecked();
  });

  it("exits past-turn mode after the last past turn", async () => {
    const user = userEvent.setup();
    const pastTurns = [
      makePastTurn(
        pastQuestionA,
        { selectedOptions: ["SMB"], otherText: "" },
        "msg-1",
        1,
      ),
    ];

    render(
      <ClarifyingQuestionBlock
        {...defaultProps}
        pastTurns={pastTurns}
        onEditPast={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(
      screen.queryByText(/Editing question 1 — changes will regenerate/),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/What is your go-to-market motion\?/),
    ).toBeInTheDocument();
  });

  it("shows Next when the past-turn draft is unchanged", async () => {
    const user = userEvent.setup();
    const pastTurns = [
      makePastTurn(
        pastQuestionA,
        { selectedOptions: ["SMB"], otherText: "" },
        "msg-1",
        1,
      ),
    ];

    render(
      <ClarifyingQuestionBlock
        {...defaultProps}
        pastTurns={pastTurns}
        onEditPast={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Previous" }));
    const nextButton = screen.getByRole("button", { name: "Next" });
    expect(nextButton).toBeInTheDocument();
    await user.click(nextButton);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows Save and regenerate and opens the modal when the draft changes", async () => {
    const user = userEvent.setup();
    const pastTurns = [
      makePastTurn(
        pastQuestionA,
        { selectedOptions: ["SMB"], otherText: "" },
        "msg-1",
        1,
      ),
    ];

    render(
      <ClarifyingQuestionBlock
        {...defaultProps}
        pastTurns={pastTurns}
        onEditPast={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("checkbox", { name: /Enterprise/ }));

    const saveButton = screen.getByRole("button", {
      name: "Save and regenerate",
    });
    expect(saveButton).toBeInTheDocument();
    await user.click(saveButton);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByText("Save and regenerate later questions?"),
    ).toBeInTheDocument();
  });

  it("modal confirm calls onEditPast with the correct arguments", async () => {
    const user = userEvent.setup();
    const onEditPast = vi.fn().mockResolvedValue(undefined);
    const pastAnswer = { selectedOptions: ["SMB"], otherText: "" };
    const pastTurns = [
      makePastTurn(pastQuestionA, pastAnswer, "msg-42", 1),
    ];

    render(
      <ClarifyingQuestionBlock
        {...defaultProps}
        pastTurns={pastTurns}
        onEditPast={onEditPast}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("checkbox", { name: /Enterprise/ }));

    await user.click(screen.getByRole("button", { name: "Save and regenerate" }));

    const dialog = screen.getByRole("dialog");
    await user.click(
      within(dialog).getByRole("button", { name: "Save and regenerate" }),
    );

    expect(onEditPast).toHaveBeenCalledTimes(1);
    expect(onEditPast).toHaveBeenCalledWith("msg-42", {
      selectedOptions: ["SMB", "Enterprise"],
      otherText: "",
    });
  });

  it("modal cancel does not call onEditPast", async () => {
    const user = userEvent.setup();
    const onEditPast = vi.fn();
    const pastTurns = [
      makePastTurn(
        pastQuestionA,
        { selectedOptions: ["SMB"], otherText: "" },
        "msg-1",
        1,
      ),
    ];

    render(
      <ClarifyingQuestionBlock
        {...defaultProps}
        pastTurns={pastTurns}
        onEditPast={onEditPast}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("checkbox", { name: /Enterprise/ }));
    await user.click(screen.getByRole("button", { name: "Save and regenerate" }));

    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    expect(onEditPast).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows the correct discardedCount in the modal", async () => {
    const user = userEvent.setup();
    const pastTurns = [
      makePastTurn(
        pastQuestionA,
        { selectedOptions: ["SMB"], otherText: "" },
        "msg-1",
        1,
      ),
      makePastTurn(
        pastQuestionB,
        { selectedOptions: ["Speed"], otherText: "" },
        "msg-2",
        2,
      ),
      makePastTurn(
        {
          question: "How will you price?",
          selection_mode: "multiple",
          options: ["Free", "Subscription"],
        },
        { selectedOptions: ["Subscription"], otherText: "" },
        "msg-3",
        3,
      ),
    ];
    const pendingQuestions = [
      pendingQuestion,
      {
        question: "Any regulatory constraints?",
        selection_mode: "multiple" as const,
        options: ["HIPAA", "GDPR", "None"],
      },
    ];

    render(
      <ClarifyingQuestionBlock
        questions={pendingQuestions}
        onSubmit={vi.fn()}
        pastTurns={pastTurns}
        onEditPast={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("checkbox", { name: /Enterprise/ }));
    await user.click(screen.getByRole("button", { name: "Save and regenerate" }));

    expect(
      screen.getByText(/discard your responses to 4 later questions/),
    ).toBeInTheDocument();
  });

  it("resets past-turn mode when the pending questions prop changes", async () => {
    const user = userEvent.setup();
    const pastTurns = [
      makePastTurn(
        pastQuestionA,
        { selectedOptions: ["SMB"], otherText: "" },
        "msg-1",
        1,
      ),
    ];

    const { rerender } = render(
      <ClarifyingQuestionBlock
        {...defaultProps}
        pastTurns={pastTurns}
        onEditPast={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(
      screen.getByText(/Editing question 1 — changes will regenerate/),
    ).toBeInTheDocument();

    const refreshedPending: ClarifyingQuestion = {
      question: "What is your pricing model?",
      selection_mode: "multiple",
      options: ["Freemium", "Usage-based"],
    };

    rerender(
      <ClarifyingQuestionBlock
        questions={[refreshedPending]}
        onSubmit={vi.fn()}
        pastTurns={pastTurns}
        onEditPast={vi.fn()}
      />,
    );

    expect(
      screen.queryByText(/Editing question 1 — changes will regenerate/),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/What is your pricing model\?/)).toBeInTheDocument();
  });
});
