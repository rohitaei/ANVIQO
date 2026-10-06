EXTRA_QUESTIONS = [
"what should I care about right now",
"what happened around PT-303",
"show me the plant story for PT-303",
"what happened yesterday around PT-303",
"have we seen this before on PT-303",
"find anything unusual in the plant",
"is PT-303 getting worse",
"give me an early warning for PT-303",
"did PT-303 recover",
"does this problem repeat",
"what does ANVI remember about the previous shift",
"what did the previous shift do",
"have we experienced this condition before",
"what happens if PT-303 continues increasing",
"show PT-303 instrument health",
"which critical instruments have no spare",
"what is the cost impact of this abnormality",
"why is energy consumption increasing",
"are there developing safety concerns",
"can I trust the current plant data",
"how confident are you about PT-303",
]
def test_extra_question_pack():
    assert len(EXTRA_QUESTIONS)==21
    assert len({q.lower() for q in EXTRA_QUESTIONS})==21
    required={"time","story","memory","unusual","worse","warning","recover","repeat","shift","before","continues","instrument","spare","cost","energy","safety","trust","confident"}
    joined=" ".join(EXTRA_QUESTIONS).lower()
    assert required <= set(x for x in required if x in joined)
