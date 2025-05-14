import os
import re
import glob
from pathlib import Path

class MarkdownKnowledgeGraph:
    def __init__(self, directory_path):
        self.directory = Path(directory_path)
        self.entity_pattern = re.compile(r'- (.*?) \[\[(.*?)\]\](?: (.*))?')
        
    def newEntity(self, name):
        """Create a new entity markdown file"""
        file_path = self.directory / f"{name}.md"
        if file_path.exists():
            return False
        
        with open(file_path, 'w') as f:
            f.write(f"# {name}\n\n")
        return True
    
    def newObservation(self, entityName, observation):
        """Add an observation to an entity, maintaining structure"""
        file_path = self.directory / f"{entityName}.md"
        if not file_path.exists():
            return False

        # Read the existing content
        with open(file_path, "r") as f:
            content = f.read()
        
        # First, check if there's already a Relationships section
        if "## Relationships" in content:
            # Insert the observation before the Relationships section
            parts = content.split("## Relationships")
            # Make sure there's proper spacing before adding observation
            if not parts[0].endswith("\n\n"):
                if parts[0].endswith("\n"):
                    parts[0] += "\n"
                else:
                    parts[0] += "\n\n"
            new_content = parts[0] + f"{observation}\n\n" + "## Relationships" + parts[1]
        else:
            # If no Relationships section, just append the observation
            new_content = content
            if new_content and not new_content.endswith("\n\n"):
                if new_content.endswith("\n"):
                    new_content += "\n"
                else:
                    new_content += "\n\n"
            new_content += f"{observation}\n\n"
        
        # Write the modified content back to the file
        with open(file_path, "w") as f:
            f.write(new_content)

        return True
    
    def newRelationship(self, entity, verbPreposition, targetEntity, context=""):
        """Add a relationship between entities"""
        file_path = self.directory / f"{entity}.md"
        if not file_path.exists():
            return False
        
        # Prevent self-referential relationships
        if entity == targetEntity:
            print(f"Warning: Prevented self-referential relationship for {entity}")
            return False
        
        # Ensure context is never None
        if context is None:
            context = ""
            
        # Read the current content
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Format the relationship line with context
        relationship_line = f"- {verbPreposition} [[{targetEntity}]]"
        if context:
            relationship_line += f" {context}"
        relationship_line += "\n"
            
        if "## Relationships" not in content:
            # If no relationships section exists, add it at the end
            if not content.endswith("\n"):
                content += "\n"
            content += "## Relationships\n" + relationship_line
        else:
            # If relationships section exists, add the relationship to it
            parts = content.split("## Relationships")
            content = parts[0] + "## Relationships" + parts[1].rstrip() + "\n" + relationship_line
        
        # Write the modified content back to the file
        with open(file_path, 'w') as f:
            f.write(content)
            
        return True
    
    def getKnowledgeGraph(self):
        """Return the complete knowledge graph as a dict of entities and relationships"""
        graph = {"entities": {}, "relationships": []}
        
        # Get all markdown files
        for file_path in self.directory.glob("*.md"):
            entity_name = file_path.stem
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract basic entity info
            lines = content.split("\n")
            observations = []
            relationships = []
            in_relationships = False
            
            for line in lines:
                if line.startswith("## Relationships"):
                    in_relationships = True
                    continue
                elif line.startswith("##"):
                    in_relationships = False
                    
                if in_relationships and line.startswith("- "):
                    # Parse relationship
                    match = self.entity_pattern.match(line)
                    if match:
                        groups = match.groups()
                        verb, target = groups[0], groups[1]
                        ctx = groups[2] if len(groups) > 2 and groups[2] is not None else ""
                        
                        # Ensure context is never None, use empty string instead
                        if ctx is None:
                            ctx = ""
                        
                        relationship = {
                            "source": entity_name,
                            "verb": verb,
                            "target": target,
                            "context": ctx
                        }
                        
                        relationships.append(relationship)
                        # Add to global relationships
                        graph["relationships"].append(relationship)
                elif not in_relationships and not line.startswith("#") and line.strip():
                    observations.append(line)
            
            # Add to graph
            graph["entities"][entity_name] = {
                "name": entity_name,
                "observations": observations,
                "relationships": relationships
            }
        
        return graph
    
    def deleteEntity(self, name):
        """Delete an entity and all related relationships"""
        file_path = self.directory / f"{name}.md"
        if not file_path.exists():
            return False
            
        # Delete the file
        os.remove(file_path)
        
        # Remove relationships in other files
        for other_file in self.directory.glob("*.md"):
            self._remove_relationships_to(other_file, name)
            
        return True
    
    def _remove_relationships_to(self, file_path, target_entity):
        """Helper to remove relationships to a specific entity"""
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            if f"[[{target_entity}]]" not in line:
                new_lines.append(line)
                
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
    
    def deleteRelationship(self, entity, verbPreposition, targetEntity, context=""):
        """Delete a specific relationship"""
        file_path = self.directory / f"{entity}.md"
        if not file_path.exists():
            return False
            
        relationship_line = f"- {verbPreposition} [[{targetEntity}]] {context}"
        found_relationship = False
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        with open(file_path, 'w') as f:
            for line in lines:
                if line.strip() == relationship_line.strip() and not found_relationship:
                    found_relationship = True
                    continue
                f.write(line)
                    
        return found_relationship
    
    def deleteObservation(self, entity, observation):
        """Delete a specific observation"""
        file_path = self.directory / f"{entity}.md"
        if not file_path.exists():
            return False
            
        found_observation = False
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        with open(file_path, 'w') as f:
            for line in lines:
                if line.strip() == observation.strip() and not found_observation:
                    found_observation = True
                    continue
                f.write(line)
                    
        return found_observation
