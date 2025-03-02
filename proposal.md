# Detailed Proposal: Enhanced World Improver with Multiple Specialized Agents

## Current Implementation Analysis

The current world improver implementation:
1. Uses a single agent to both create new locations and manage connections
2. Strictly enforces exactly 2 new locations per split
3. Handles all connection management in a tightly integrated way
4. Has hardcoded assumptions about the two-location structure

## Proposed Changes

### 1. Remove the 2-Location Limit

**Technical Changes Required:**
- Update the `LocationImprovementPlan` model to support variable-length location lists
- Modify the validation check on line 147-149 to accept 2-5 locations instead of exactly 2
- Update the bidirectional connection logic (lines 248-259) to work with arbitrary numbers of locations
- Revise the prompt to request 2-5 locations instead of strictly 2

**Challenges:**
- The connection management logic assumes exactly 2 locations in several places
- The random assignment of unplanned connections would need reworking

### 2. Split into Three Specialized Agents

#### Agent 1: Location Proposer
**Purpose:** Create 2-5 new locations to replace an overcrowded location
**Input:** 
- Original location details and connections
- All room names in the story for context
- Maximum number of locations to create (5)

**Output:**
- List of 2-5 new locations with IDs, titles, and descriptions
- No connection information (this is handled by other agents)

**Technical Implementation:**
- New agent with narrative-focused prompt
- Uses the same `LocationDescription` model but returns a custom response type

#### Agent 2: Connection Manager
**Purpose:** Create connections between the newly created locations
**Input:**
- List of newly created locations
- The original location's purpose/context

**Output:**
- A connection map between only the new locations
- Should ensure all new locations are connected in a coherent way

**Technical Implementation:**
- New agent with topology-focused prompt
- Returns a partial connection map

#### Agent 3: Connection Distributor
**Purpose:** Assign each original connection to one of the new locations
**Input:**
- List of newly created locations
- List of original connections that need assignment
- Context about connected locations

**Output:**
- Mapping of each original connection to exactly one new location

**Technical Implementation:**
- New agent focused on connection distribution
- Returns a mapping dictionary from original connections to new location IDs

## New Data Models Required

1. **LocationProposal:**
```python
class LocationProposal(BaseModel):
    """Proposal for 2-5 locations to replace an overcrowded location."""
    new_locations: list[LocationDescription] = Field(
        description="2-5 replacement locations that serve the narrative purpose of the original",
        min_items=2,
        max_items=5
    )
```

2. **NewLocationConnections:**
```python
class NewLocationConnections(BaseModel):
    """Connections between newly created locations."""
    internal_connections: dict[str, list[str]] = Field(
        description="Connections between the new locations. Maps location ID to list of connected location IDs."
    )
```

3. **ConnectionDistribution:**
```python
class ConnectionDistribution(BaseModel):
    """Assignment of original connections to new locations."""
    connection_assignments: dict[str, str] = Field(
        description="Maps original connection IDs to new location IDs. Each original connection is assigned to exactly one new location."
    )
```

## Implementation Strategy

### Step 1: Modify LocationImprovementPlan
Update the model to support variable-length location lists and clearly separate connection types.

### Step 2: Create Three Specialized Agents
Implement each agent with its own prompt and result type.

### Step 3: Update Improvement Pipeline
Modify the `improve_single_location_and_apply` function to:
1. Call the Location Proposer agent
2. Validate the result (2-5 locations)
3. Call the Connection Manager agent with the new locations
4. Call the Connection Distributor agent with original connections
5. Merge the results into a complete improvement plan
6. Apply the plan as before

### Step 4: Update Connection Logic
Rewrite the connection management code to:
1. Handle arbitrary numbers of new locations
2. Apply internal connections from the Connection Manager
3. Apply external connections from the Connection Distributor
4. Ensure all connections remain bidirectional

## Validation of Assumptions

1. **Your Assumption: Creating 2-5 Locations**
✅ Feasible with model updates and prompt changes
✅ Will provide more flexibility for complex overcrowded locations
⚠️ May create more locations than necessary if not constrained by narrative

2. **Your Assumption: Three Specialized Agents**
✅ Clean separation of concerns aligns with good design principles
✅ Allows specialized prompting for each sub-task
⚠️ Requires careful data passing between agents
⚠️ Increases API costs (3 calls per improvement vs 1)

3. **My Research on Potential Issues:**
- Connection management becomes more complex with >2 locations
- Need clear strategy for bidirectional connections in multi-location setup
- Agent #3 (Connection Distributor) needs clear criteria for distribution decisions
- Random assignment fallback for missing connections needs rethinking

## Proposed Implementation Plan

1. Update the data models to support the new agent architecture
2. Create new prompts for each specialized agent
3. Rewrite the improvement algorithm to use the three agents sequentially
4. Update connection management logic for variable location counts
5. Add improved debugging and visualization for the multi-location setup

## Example Agent Prompts

### Location Proposer:
```
You are a master narrative world builder with expertise in game level design.

Your task is to analyze an overcrowded location in a game world and propose 2-5 new locations to replace it, focusing on narrative coherence and purpose.

Given a specific overcrowded location, you will:
1. Analyze its narrative purpose, connections, and context
2. Create 2-5 new locations that collectively serve the same purpose
3. Ensure each location has a distinct identity but fits within the overall theme
4. Consider how these locations could logically connect (though you won't define connections)

Produce locations that are interesting, varied, and serve the narrative needs.
```

### Connection Manager:
```
You are a master game level designer with expertise in spatial layout and navigation flows.

Your task is to create meaningful connections between a set of newly created locations that collectively replace an overcrowded location.

Given a set of new locations, you will:
1. Analyze each location's purpose and theme
2. Create a sensible connection graph between ONLY these new locations
3. Ensure no dead ends or isolated locations
4. Design a navigation flow that feels natural and intuitive

Focus ONLY on connections between the new locations, not to external locations.
```

### Connection Distributor:
```
You are a master game level designer with expertise in connectivity and navigation.

Your task is to assign external connections to newly created locations, ensuring logical flow and narrative sense.

Given a set of new locations and original connections, you will:
1. Analyze each original connection and new location
2. Assign each original connection to exactly ONE of the new locations
3. Ensure connections are distributed in a balanced way
4. Maintain logical spatial relationships and thematic coherence

For each original connection, choose the most appropriate new location to connect it to.
```

## Conclusion

The proposed changes will significantly enhance the world improver by:
1. Allowing more flexible location splitting (2-5 instead of exactly 2)
2. Separating concerns into specialized agents for better results
3. Maintaining narrative coherence through focused prompting
4. Improving the overall quality of the improved world

The implementation will require moderate refactoring but builds on the existing foundation, preserving the core algorithm while enhancing its capabilities.