---
name: rewrite-summarize
description: |
  When the user requires to summarize a given text, use this skill. This is an updated version of the default summarization skill.
---
Don't summarize in the default way, rewrite it following these rules:

First and foremost, **always confirm with the user the range of text to be summarized**. Confirm before proceeding. For example, if the user provides a text with multiple chapters, confirm with the user which chapter(s) to summarize.

**Your goal**: 
Convey every substantive idea, argument, and insight from this text in the clearest, most well-structured way possible — as if written by someone who respects the reader's time and intelligence.

**Style principles**:
Clarity is king. Every sentence must earn its place. If it doesn't introduce a new idea, support an argument, or add necessary context — cut it. Kill clutter. Remove filler phrases, redundant examples, padding anecdotes that don't serve the point, and repetition that exists to fill pages rather than deepen understanding. 
Use accurate and direct language, adopt an active voice. Employ short sentences when they work. Keep only the academic jargons, and define them in scholarly terms with some background knowledge if necessary. Drop the colloquialisms.
Logical architecture. Reorganize the flow if the original is scattered. Ideas should build on each other. The reader should never wonder "why are we talking about this now?" On the other hand, if the original text skillfully presents some intellectual obstacles for the reader to ponder upon, you should preserve them in the form of an explicit question or puzzle so as to respect the reader's agency.
Preserve what matters. Keep important examples, key stories, and nuance that genuinely earn their place. Concise does not mean shallow.
Last but not least, point out the limitations of the original text if it is shallow or inconsistent in itself.

**Output format**:
- Use clear headings and subheadings to structure the summary.
- Use bullet points or numbered lists for key ideas, arguments, and examples.
- Use bold text to highlight key terms and concepts.
- Use italics to highlight important examples, key stories, and nuance.
