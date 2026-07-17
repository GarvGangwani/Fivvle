import { Extension } from "@tiptap/core";

export interface FontSizeOptions {
  /** Node/mark types that accept the fontSize attribute. */
  types: string[];
}

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    fontSize: {
      /** Set an explicit font size (e.g. "18px"). */
      setFontSize: (size: string) => ReturnType;
      /** Remove the font size attribute, reverting to the default. */
      unsetFontSize: () => ReturnType;
    };
  }
}

/**
 * Adds a `fontSize` attribute to the `textStyle` mark. Tiptap v2 has no
 * official font-size extension, so this follows the standard v2 pattern of
 * extending TextStyle with a global attribute. Exported for reuse by future
 * editors.
 */
export const FontSize = Extension.create<FontSizeOptions>({
  name: "fontSize",

  addOptions() {
    return {
      types: ["textStyle"],
    };
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (element) => element.style.fontSize || null,
            renderHTML: (attributes) => {
              if (!attributes.fontSize) {
                return {};
              }
              return { style: `font-size: ${attributes.fontSize}` };
            },
          },
        },
      },
    ];
  },

  addCommands() {
    return {
      setFontSize:
        (size) =>
        ({ chain }) =>
          chain().setMark("textStyle", { fontSize: size }).run(),
      unsetFontSize:
        () =>
        ({ chain }) =>
          chain()
            .setMark("textStyle", { fontSize: null })
            .removeEmptyTextStyle()
            .run(),
    };
  },
});

export default FontSize;
