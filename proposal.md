# Detailed Proposal: Enhanced World Improver with Multiple Specialized Agents

## Current Implementation Analysis

The current world improver implementation:
1. Uses a single agent to both create new locations and manage connections
2. Strictly enforces exactly 2 new locations per split
3. Handles all connection management in a tightly integrated way
4. Has hardcoded assumptions about the two-location structure

## Proposed Changes

### Split into Three Specialized Agents

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

```python
class _LocationProposal(BaseModel):
    """Proposal for 2-5 locations to replace an overcrowded location."""
    new_locations: list[LocationDescription] = Field(
        description="2-5 replacement locations that serve the narrative purpose of the original",
        min_items=2,
        max_items=5
    )
```
- New agent with narrative-focused prompt
- Outputs new type _LocationProposal
- Create a function `propose_replacement_locations` which calls agent

#### Agent 2: Connection Manager
**Purpose:** Create connections between the newly created locations
**Input:**
- List of newly created locations
- The original location's purpose/context

**Output:**
- A connection map between only the new locations
- Should ensure all new locations are connected in a coherent way

**Technical Implementation:**
```python
class _NewLocationConnections(BaseModel):
    """Connections between newly created locations."""
    internal_connections: dict[str, list[str]] = Field(
        description="Connections between the new locations. Maps location ID to list of connected location IDs."
    )
```
- New agent with topology-focused prompt
- Returns a partial connection map (_NewLocationConnections)
- Agent code should not be called if only 2 locations are proposed. In that case we should automatically connect the two rooms to each-other
- Should have validations logic to insure every location has at least one connection
- Create a function `propose_replacement_location_interconnections`

#### Agent 3: Connection Distributor
**Purpose:** Assign each original connection to one of the new locations
**Input:**
- List of newly created locations
- List of original connections that need assignment. Each connection should include context about the location it connects to.

**Output:**
- Mapping of each original connection to exactly one new location

**Technical Implementation:**
```python
class _ConnectionDistribution(BaseModel):
    """Assignment of original connections to new locations."""
    connection_assignments: dict[str, str] = Field(
        description="Maps original connection IDs to new location IDs. Each original connection is assigned to exactly one new location."
    )
```
- New agent focused on connection distribution
- Returns a mapping dictionary from original connections to new location IDs (_ConnectionDistribution)
- Create function `redistribute_connections`
- Should validate that all connections were assigned correctly
- If validation fails it should produce an error

### Update Improvement Pipeline
Remove improve_single_location.

Update the `improve_single_location_and_apply` function to work directly with the three specialized agents' outputs:
- First it calls propose_replacement_locations
* If no new locations are proposed, we can exit
* Remove the old locations
* Add the new locations
- Next we call propose_replacement_location_interconnections
* Add the new connections
- Finally we call redstribute_connections
* Add all the necessary connections


### Remove handle_missing_connections
handle_missing_connections should no longer be needed. The new logic insures that there are no missing connections


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
5. Eliminating the need for an intermediate LocationImprovementPlan data model
6. Making the code more direct by working with agent outputs directly

The implementation will require moderate refactoring but builds on the existing foundation, simplifying the architecture while enhancing its capabilities. By removing the intermediate data model conversion, we not only make the code more straightforward but also more maintainable and easier to extend in the future.
