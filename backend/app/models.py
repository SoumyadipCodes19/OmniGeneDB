from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# Pydantic Models for API
class RunCreate(BaseModel):
    accession: str
    case_group: str
    control_group: str
    top_n: int = 15
    is_cancer: bool = False

class RunResponse(BaseModel):
    id: str
    accession: str
    case_group: str
    control_group: str
    top_n: int = 15
    is_cancer: bool = False
    status: str
    created_at: datetime
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RunResultItem(BaseModel):
    symbol: str
    log2fc: Optional[float] = None
    padj: Optional[float] = None
    baseMean: Optional[float] = None
    uniprot: Optional[Dict[str, Any]] = None
    kegg: Optional[Dict[str, Any]] = None
    pdb: Optional[Dict[str, Any]] = None
    alphafold_url: Optional[str] = None
    string: Optional[Dict[str, Any]] = None
    clinvar: Optional[Dict[str, Any]] = None
    genomic: Optional[Dict[str, Any]] = None
    drugs: Optional[List[str]] = None
    depmap_essential: Optional[bool] = False
    eqtl: Optional[List[Dict[str, Any]]] = None
    tcga_survival: Optional[bool] = False
    consistency_flag: Optional[bool] = True
    consistency_note: Optional[str] = ""
    coverage_gaps: Optional[List[str]] = []

    model_config = ConfigDict(extra="allow", from_attributes=True)

class RunResultData(BaseModel):
    results: List[RunResultItem] = []
    master_tfs: List[str] = []
    ppi_network: Optional[List[Dict[str, Any]]] = None
    immune_fractions: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class RunResultResponse(RunResponse):
    results: Optional[RunResultData] = None

# SQLAlchemy Models
from sqlalchemy import Column, String, DateTime, JSON, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Run(Base):
    __tablename__ = "runs"
    
    id = Column(String, primary_key=True, index=True)
    accession = Column(String, index=True)
    case_group = Column(String)
    control_group = Column(String)
    top_n = Column(Integer, default=15)
    is_cancer = Column(Boolean, default=False)
    status = Column(String) # 'queued', 'analyzing_deseq2', 'integrating_databases', 'completed', 'failed'
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(String, nullable=True)
    results = Column(JSON, nullable=True)
