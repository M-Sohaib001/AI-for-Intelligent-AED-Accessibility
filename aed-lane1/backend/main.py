import sys
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

# Ensure backend directory is in Python path
sys.path.append(os.path.dirname(__file__))

from graph_utils import load_or_create_graph, load_aed_dataset, snap_aeds_to_graph
from ranking import baseline_rank, network_rank
from abstention import determine_abstention

app = FastAPI(title="AED Discovery & Routing Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize in-memory Graph & AED dataset
G = load_or_create_graph()
from graph_utils import validate_graph
print(validate_graph(G))
RAW_AEDS = load_aed_dataset()
AEDS_SNAPPED = snap_aeds_to_graph(G, RAW_AEDS)

MAX_WALK_DISTANCE_M = 1200.0

class RankRequest(BaseModel):
    start_lat: float
    start_lon: float
    datetime: datetime

    @field_validator("start_lat")
    @classmethod
    def validate_lat(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("start_lat out of bounds")
        return v

    @field_validator("start_lon")
    @classmethod
    def validate_lon(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("start_lon out of bounds")
        return v


class RankedResult(BaseModel):
    aed_id: str
    distance_m: float
    modeled_walk_time_min: float
    flags: list[str] = []
    snap_quality: str
    geometry: list[list[float]] = []


class BaselineResult(BaseModel):
    aed_id: str
    straight_line_m: float


class RankResponse(BaseModel):
    ranked: list[RankedResult]
    baseline: list[BaselineResult]
    abstained: bool
    abstain_reason: str | None = None
    safety_banner: str = (
        "Prototype for planning and simulation only — not for emergency use. "
        "In an emergency in Singapore, call 995 immediately and follow SCDF instructions."
    )


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "nodes_loaded": G.number_of_nodes(),
        "aeds_loaded": len(AEDS_SNAPPED)
    }


@app.post("/rank_aeds", response_model=RankResponse)
def rank_aeds(req: RankRequest):
    if not AEDS_SNAPPED:
        raise HTTPException(status_code=500, detail="AED dataset not loaded.")

    try:
        baseline_res = baseline_rank(req.start_lat, req.start_lon, AEDS_SNAPPED)
        ranked_res, feasibility_log = network_rank(
            req.start_lat, req.start_lon, G, AEDS_SNAPPED, req.datetime, max_distance_m=MAX_WALK_DISTANCE_M
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Routing failed: {str(e)}")

    abstention = determine_abstention(ranked_res, feasibility_log)

    return RankResponse(
        ranked=[
            RankedResult(
                aed_id=r["aed_id"],
                distance_m=r["distance_m"],
                modeled_walk_time_min=r["modeled_walk_time_min"],
                flags=r.get("data_quality", {}).get("location_flags", []),
                snap_quality=r.get("graph_info", {}).get("snap_quality", "acceptable"),
                geometry=r.get("geometry", [])
            ) for r in ranked_res
        ],
        baseline=[
            BaselineResult(
                aed_id=b["aed_id"],
                straight_line_m=b["straight_line_m"]
            ) for b in baseline_res
        ],
        abstained=abstention["abstained"],
        abstain_reason=abstention["reason"].value if abstention["reason"] else None
    )