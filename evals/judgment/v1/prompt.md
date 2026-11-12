You are an agent in a software delivery workflow. {context}

Below is everything you can see at this point. Decide what to do next.

Classify the decision as exactly one of:

- BLOCK — an ambiguity or defect is material enough that continuing would risk implementing or validating the wrong thing. You raise it and stop the affected work.
- FLAG_AND_CONTINUE — there is a real ambiguity or concern, but what you have still lets you make correct progress. You surface it and continue the work that remains valid.
- NO_FINDING — nothing here needs a human: any apparent ambiguity is immaterial, already answered, or does not change the decision. You consume no human round trip.

Then choose your next action from this list — exactly one id:

{actions}

<<<SNAPSHOT
{snapshot}
SNAPSHOT>>>

Answer with JSON only, no prose, no code fence:
{"decision": "BLOCK" | "FLAG_AND_CONTINUE" | "NO_FINDING", "next_action": "<one id from the list>", "surfaced": "<the question or finding you would put to the human, in one or two sentences — or null when there is none>", "rationale": "<why, in two or three sentences>"}
