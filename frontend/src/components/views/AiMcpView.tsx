import React from 'react';
import { Sparkles, Terminal, Shield, Check, Cpu } from 'lucide-react';

export const AiMcpView: React.FC = () => {
  const mcpTools = [
    {
      name: 'list_commitments',
      description: 'Fetch permission-filtered customer promises for the authenticated tenant.',
      category: 'Read',
    },
    {
      name: 'get_commitment_evidence',
      description: 'Retrieve linked Jira tickets, audio segment quotes, and delivery verification.',
      category: 'Read',
    },
    {
      name: 'investigate_commitment',
      description: 'Analyze schedule conflicts and reason through ticket dependency blockers.',
      category: 'Analysis',
    },
    {
      name: 'create_update_draft',
      description: 'Draft proactive update for Slack/Email. Requires human approval before delivery.',
      category: 'Mutation (Approval Gated)',
    },
  ];

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-6xl mx-auto w-full">
      <div className="pb-6 border-b border-neutral-200">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900">
          AI & Model Context Protocol (MCP)
        </h1>
        <p className="text-xs sm:text-sm text-neutral-500 mt-1">
          Manage LLM extraction pipelines, versioned prompt templates, and external MCP tools.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-6">
        {/* Model Pipeline Card */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-5 shadow-2xs">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-8 h-8 rounded-lg bg-neutral-900 text-white flex items-center justify-center">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-neutral-900">Extraction Model Pipeline</h3>
              <span className="text-[11px] text-emerald-600 font-semibold">● Active (gemini-2.5-pro)</span>
            </div>
          </div>

          <p className="text-xs text-neutral-600 mb-4">
            Structured JSON extraction with strict schema validation. Verifies speaker attestation,
            due date conditions, and confidence scoring.
          </p>

          <div className="space-y-2 text-xs bg-neutral-50 p-3 rounded-xl border border-neutral-200/80 font-mono text-neutral-700">
            <div>Provider: Google AI Studio / Vertex AI</div>
            <div>Extraction prompt: v2.4 (Strict commitment policy)</div>
            <div>Safety filters: PII Redaction enabled</div>
          </div>
        </div>

        {/* MCP Server Card */}
        <div className="bg-white border border-neutral-200 rounded-2xl p-5 shadow-2xs">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-8 h-8 rounded-lg bg-neutral-900 text-white flex items-center justify-center">
              <Terminal className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-neutral-900">PromiseCheck MCP Server</h3>
              <span className="text-[11px] text-neutral-600 font-semibold">Endpoint: /mcp</span>
            </div>
          </div>

          <p className="text-xs text-neutral-600 mb-4">
            Exposes controlled Model Context Protocol tools for Cursor, Claude Desktop, and autonomous
            investigation agents.
          </p>

          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <Shield className="w-4 h-4 text-neutral-700 shrink-0" />
            <span>Tenant authentication enforced. Scopes validated per tool invocation.</span>
          </div>
        </div>
      </div>

      {/* Tools Table */}
      <div className="bg-white border border-neutral-200 rounded-2xl p-5 shadow-2xs mt-6">
        <h3 className="font-bold text-sm text-neutral-900 mb-4">Registered MCP Tool Catalog</h3>

        <div className="space-y-3">
          {mcpTools.map((tool) => (
            <div
              key={tool.name}
              className="p-3.5 border border-neutral-100 rounded-xl hover:bg-neutral-50/60 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
            >
              <div>
                <code className="font-mono font-bold text-neutral-900 bg-neutral-100 px-2 py-0.5 rounded border border-neutral-200">
                  {tool.name}
                </code>
                <p className="text-neutral-600 mt-1">{tool.description}</p>
              </div>

              <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-neutral-100 text-neutral-700 self-start sm:self-auto shrink-0">
                {tool.category}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
