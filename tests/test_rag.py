from core.rag import chunk_documents, retrieve


def test_chunking_preserves_filename_and_overlap():
    text = "alpha " * 200
    chunks = chunk_documents([{"filename": "policy.txt", "content": text}], size=100, overlap=20)
    assert len(chunks) > 1
    assert chunks[0]["filename"] == "policy.txt"
    assert chunks[0]["chunk"] == 1
    assert chunks[0]["text"][-20:] == chunks[1]["text"][:20]


def test_retrieval_ranks_relevant_document():
    docs = [
        {"filename": "attendance.txt", "content": "Students must maintain at least 75 percent attendance in each course."},
        {"filename": "exam.txt", "content": "Examination dates are listed in the academic calendar."},
    ]
    matches = retrieve("What is the attendance requirement?", docs)
    assert matches
    assert matches[0]["filename"] == "attendance.txt"
    assert matches[0]["score"] > 0


def test_chunk_size_must_exceed_overlap():
    try:
        chunk_documents([], size=10, overlap=10)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid chunk sizes should fail")
