import type { MDXComponents } from "mdx/types";

// Required by @next/mdx in the App Router. Styling comes from .prose-av on the docs layout.
export function useMDXComponents(components: MDXComponents): MDXComponents {
  return { ...components };
}
