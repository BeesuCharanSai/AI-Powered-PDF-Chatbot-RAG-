import { Client } from '@langchain/langgraph-sdk';

/**
 * Thin wrapper around the LangGraph SDK client with a few convenience
 * helpers. This talks directly to the LangGraph API server (started via
 * `langgraph dev` in the backend) from the browser -- there is no Next.js
 * server layer in this app, so all calls happen client-side.
 */
class LangGraphBase {
  constructor(client) {
    this.client = client;
  }

  /** Creates a new thread with optional metadata */
  async createThread(metadata) {
    return this.client.threads.create({ metadata });
  }

  /** Gets a thread by ID */
  async getThread(threadId) {
    return this.client.threads.get(threadId);
  }

  /** Searches for threads with optional metadata filters */
  async searchThreads(params = {}) {
    return this.client.threads.search({
      metadata: params.metadata,
      limit: params.limit || 10,
      offset: params.offset || 0,
    });
  }

  /** Gets the current state of a thread */
  async getThreadState(threadId) {
    return this.client.threads.getState(threadId);
  }

  /** Updates the state of a thread */
  async updateThreadState(threadId, values, asNode) {
    return this.client.threads.updateState(threadId, { values, asNode });
  }

  /** Deletes a thread by ID */
  async deleteThread(threadId) {
    return this.client.threads.delete(threadId);
  }

  /** Gets the history of a thread's states */
  async getThreadHistory(threadId, limit = 10) {
    return this.client.threads.getHistory(threadId, { limit });
  }
}

let clientInstance = null;

export const createClient = () => {
  if (clientInstance) {
    return clientInstance;
  }

  const apiUrl = import.meta.env.VITE_LANGGRAPH_API_URL;
  if (!apiUrl) {
    throw new Error('VITE_LANGGRAPH_API_URL is not set');
  }

  const client = new Client({ apiUrl });
  clientInstance = new LangGraphBase(client);
  return clientInstance;
};

export const client = createClient();
