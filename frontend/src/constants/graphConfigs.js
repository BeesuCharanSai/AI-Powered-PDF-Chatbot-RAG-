/**
 * The configuration for the retrieval assistant's streaming runs.
 */
export const retrievalAssistantStreamConfig = {
  query_model: 'groq/llama-3.3-70b-versatile',
  retriever_provider: 'supabase',
  k: 5,
};

/**
 * The configuration for the indexing/ingestion process.
 */
export const indexConfig = {
  use_sample_docs: false,
  retriever_provider: 'supabase',
};
