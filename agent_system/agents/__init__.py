# Persona Inc. — Agent Registry（全11エージェント）
from agent_system.agents.ceo_agent        import CeoAgent
from agent_system.agents.qa_agent         import QaAgent
from agent_system.agents.accounting_agent import AccountingAgent
from agent_system.agents.legal_agent      import LegalAgent
from agent_system.agents.cfo_agent        import CfoAgent
from agent_system.agents.cpo_agent        import CpoAgent
from agent_system.agents.cmo_agent        import CmoAgent
from agent_system.agents.research_agent   import ResearchAgent
from agent_system.agents.cto_agent        import CtoAgent
from agent_system.agents.cs_agent         import CsAgent
from agent_system.agents.ga_agent         import GaAgent

AGENT_REGISTRY = {
    # C-Suite (Opus)
    "ceo":        CeoAgent,
    "legal":      LegalAgent,
    # Business (Sonnet)
    "cfo":        CfoAgent,
    "cpo":        CpoAgent,
    "cmo":        CmoAgent,
    "research":   ResearchAgent,
    "cto":        CtoAgent,
    # Support (Haiku)
    "qa":         QaAgent,
    "accounting": AccountingAgent,
    "cs":         CsAgent,
    "ga":         GaAgent,
}

def get_agent(agent_id: str):
    cls = AGENT_REGISTRY.get(agent_id)
    if not cls:
        raise ValueError(f"Unknown agent: {agent_id}. Available: {list(AGENT_REGISTRY.keys())}")
    return cls()
