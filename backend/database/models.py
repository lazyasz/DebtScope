"""
SQLAlchemy ORM models for Multi-Tenant Technical Debt Intelligence Platform.
Defines schemas for Users, Workspaces, Memberships, Repositories, Files,
Engineering Metrics, ML Predictions, Business Context, Priority Scores, and Integrations.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from backend.database.connection import Base


def utc_now():
    """Generates UTC timestamp compatible across Python 3.14+."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(100), primary_key=True, index=True) # e.g. usr_lead_01 or google sub
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    memberships = relationship("WorkspaceMembership", back_populates="user", cascade="all, delete-orphan")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(100), primary_key=True, index=True) # e.g. ws_demo or ws_uuid
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(String(100), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_demo = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    memberships = relationship("WorkspaceMembership", back_populates="workspace", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(100), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="ENGINEER") # OWNER, ADMIN, ENGINEER, VIEWER
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uix_workspace_user"),)

    workspace = relationship("Workspace", back_populates="memberships")
    user = relationship("User", back_populates="memberships")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    name = Column(String(100), nullable=False, index=True)
    url = Column(String(255), nullable=True)
    default_branch = Column(String(50), default="main")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uix_workspace_repo_name"),)

    # Relationships
    workspace = relationship("Workspace", back_populates="repositories")
    files = relationship("SourceFile", back_populates="repository", cascade="all, delete-orphan")


class SourceFile(Base):
    __tablename__ = "source_files"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(255), nullable=False, index=True)
    file_name = Column(String(100), nullable=False)
    language = Column(String(50), default="Python")
    lines_of_code = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    repository = relationship("Repository", back_populates="files")
    metrics = relationship("EngineeringMetric", back_populates="file", uselist=False, cascade="all, delete-orphan")
    debt_items = relationship("TechnicalDebtItem", back_populates="file", cascade="all, delete-orphan")
    prediction = relationship("MLPrediction", back_populates="file", uselist=False, cascade="all, delete-orphan")
    business_context = relationship("BusinessContext", back_populates="file", uselist=False, cascade="all, delete-orphan")
    priority_score = relationship("PriorityScore", back_populates="file", uselist=False, cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="file", cascade="all, delete-orphan")


class EngineeringMetric(Base):
    __tablename__ = "engineering_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    file_id = Column(Integer, ForeignKey("source_files.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Code Quality & Static Metrics (Normalized or absolute)
    cyclomatic_complexity = Column(Float, default=1.0)
    cognitive_complexity = Column(Float, default=1.0)
    code_smells_count = Column(Integer, default=0)
    duplication_pct = Column(Float, default=0.0)      # 0 to 100%
    test_coverage_pct = Column(Float, default=100.0)  # 0 to 100%
    code_churn_commits = Column(Integer, default=0)
    bug_frequency = Column(Integer, default=0)
    
    # Metric Provenance Tag: MEASURED, ESTIMATED, USER_RULE, DEFAULT
    coverage_provenance = Column(String(30), default="ESTIMATED")
    churn_provenance = Column(String(30), default="ESTIMATED")
    
    # Normalized Technical Risk Score (0–100) computed from static metrics
    technical_risk_score = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    file = relationship("SourceFile", back_populates="metrics")


class TechnicalDebtItem(Base):
    __tablename__ = "technical_debt_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    file_id = Column(Integer, ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_category = Column(String(50), nullable=False) # e.g. "COMPLEXITY", "DUPLICATION", "SMELL", "SECURITY"
    severity = Column(String(20), default="MEDIUM")    # LOW, MEDIUM, HIGH, CRITICAL
    debt_age_days = Column(Integer, default=30)
    description = Column(Text, nullable=False)
    line_number = Column(Integer, nullable=True)
    remediation_guidance = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    file = relationship("SourceFile", back_populates="debt_items")


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    file_id = Column(Integer, ForeignKey("source_files.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # ML Model Outputs (0–100 scale or probability * 100)
    predicted_future_risk = Column(Float, default=50.0) # 0 to 100
    defect_probability = Column(Float, default=0.5)     # 0.0 to 1.0
    churn_risk_score = Column(Float, default=50.0)      # 0 to 100
    confidence_score = Column(Float, default=0.85)      # 0.0 to 1.0
    model_version = Column(String(50), default="random-forest-szz-v1")
    prediction_timestamp = Column(DateTime, default=utc_now)

    file = relationship("SourceFile", back_populates="prediction")


class BusinessContext(Base):
    __tablename__ = "business_contexts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    file_id = Column(Integer, ForeignKey("source_files.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Business attributes (0–100 scale)
    business_criticality = Column(Float, default=50.0)          # Core revenue/transaction role
    customer_impact = Column(Float, default=50.0)               # User-facing failure severity
    module_criticality = Column(Float, default=50.0)            # Structural architecture importance
    release_proximity = Column(Float, default=50.0)             # Next release milestone closeness
    sprint_urgency = Column(Float, default=50.0)                # Current sprint priority/deliverables
    maintenance_cost = Column(Float, default=50.0)              # Dev friction & recurring overhead
    estimated_remediation_effort = Column(Float, default=50.0)  # Difficulty & hours to fix (0=easiest, 100=hardest)
    
    domain_tag = Column(String(50), default="core")             # e.g., "payment", "auth", "analytics", "ui"
    provenance = Column(String(30), default="DEFAULT")          # MEASURED, ESTIMATED, USER_RULE, DEFAULT
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    file = relationship("SourceFile", back_populates="business_context")


class PriorityScore(Base):
    __tablename__ = "priority_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    file_id = Column(Integer, ForeignKey("source_files.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Computed scores (0–100 scale)
    composite_technical_risk = Column(Float, default=0.0)
    composite_business_impact = Column(Float, default=0.0)
    urgency_score = Column(Float, default=0.0)
    baseline_score = Column(Float, default=0.0)
    final_priority_score = Column(Float, default=0.0)
    
    priority_level = Column(String(20), default="LOW") # LOW, MEDIUM, HIGH, CRITICAL
    roi_score = Column(Float, default=100.0)           # Value / Effort ratio
    quadrant = Column(String(50), default="OPPORTUNISTIC") # QUICK_WIN, STRATEGIC_REFACTOR, OPPORTUNISTIC, DEPRIORITIZED
    rank = Column(Integer, default=1)
    
    # Missing dimensions & dynamic coverage metadata (ADR 010)
    scored_dimensions_count = Column(Integer, default=5)
    dimension_coverage = Column(String(50), default="5 of 5 dimensions")
    missing_dimensions_json = Column(Text, default="[]")
    
    calculated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    file = relationship("SourceFile", back_populates="priority_score")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    file_id = Column(Integer, ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False, index=True)
    
    recommendation_type = Column(String(50), nullable=False) # "REFACTOR_IMMEDIATELY", "SPRINT_CANDIDATE", "SCHEDULE_FUTURE", "MONITOR"
    action_summary = Column(String(255), nullable=False)
    rationale = Column(Text, nullable=False)
    sprint_target = Column(String(50), default="Next Sprint")
    estimated_story_points = Column(Integer, default=3)
    created_at = Column(DateTime, default=utc_now)

    file = relationship("SourceFile", back_populates="recommendations")


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    user_id = Column(String(100), nullable=False, default="usr_lead_01", index=True)
    provider = Column(String(50), nullable=False, index=True) # "github", "jira", "notion", "google"
    provider_account_id = Column(String(100), nullable=True)
    provider_account_name = Column(String(200), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    
    # Encrypted credential tokens
    access_token_enc = Column(Text, nullable=True)
    refresh_token_enc = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    scopes = Column(Text, nullable=True)
    
    # Status: "CONNECTED", "DISCONNECTED", "EXPIRED", "ERROR"
    status = Column(String(30), default="CONNECTED", index=True)
    error_message = Column(Text, nullable=True)
    
    # JSON metadata for selected resources, webhook IDs, and provider configuration
    metadata_json = Column(Text, default="{}")
    
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String(100), primary_key=True, index=True)  # e.g. job_uuid
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True)
    repo_url = Column(String(255), nullable=False)
    
    # Status: QUEUED, CLONING, ANALYZING, MINING, COMPLETED, FAILED, CANCELLED
    status = Column(String(30), default="QUEUED", index=True)
    stage = Column(String(100), default="Queued for analysis")
    progress_pct = Column(Integer, default=0)  # 0 to 100
    
    error_message = Column(Text, nullable=True)
    result_summary = Column(Text, nullable=True)  # JSON summary
    files_analyzed = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=utc_now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class CopilotConversation(Base):
    __tablename__ = "copilot_conversations"

    id = Column(String(100), primary_key=True, index=True)  # conv_<uuid>
    workspace_id = Column(String(100), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default="ws_demo", index=True)
    user_id = Column(String(100), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), default="New Copilot Session")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    messages = relationship("CopilotMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="CopilotMessage.created_at")


class CopilotMessage(Base):
    __tablename__ = "copilot_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(100), ForeignKey("copilot_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(30), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=True)  # JSON list of citations
    tool_calls_json = Column(Text, nullable=True)  # JSON list of tool executions
    refactor_diff = Column(Text, nullable=True)  # Verified before/after AST diff
    created_at = Column(DateTime, default=utc_now)

    conversation = relationship("CopilotConversation", back_populates="messages")


