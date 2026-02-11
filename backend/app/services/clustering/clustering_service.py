"""Service for clustering similar requirements across frameworks."""

import uuid
from typing import Optional
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.unified_framework import (
    FrameworkRequirement,
    RequirementCluster,
    RequirementClusterMember,
    ClusterType,
)
from app.services.clustering.similarity_service import SimilarityService


class ClusteringService:
    """Service for clustering similar requirements.

    Uses hierarchical agglomerative clustering to group semantically similar
    requirements across frameworks, reducing interview burden by allowing
    a single question to cover multiple related requirements.
    """

    def __init__(self, db: Session):
        self.db = db
        self.similarity_service = SimilarityService(db)

    def generate_clusters(
        self,
        framework_ids: Optional[list[uuid.UUID]] = None,
        threshold: float = 0.85,
        min_cluster_size: int = 2,
        cluster_type: ClusterType = ClusterType.SEMANTIC,
    ) -> list[RequirementCluster]:
        """Generate requirement clusters using hierarchical agglomerative clustering.

        Args:
            framework_ids: Frameworks to include (None for all)
            threshold: Similarity threshold for clustering (0.0 to 1.0)
            min_cluster_size: Minimum requirements to form a cluster
            cluster_type: Type of cluster to create

        Returns:
            List of created RequirementCluster objects
        """
        # Build similarity matrix
        requirements, similarity_matrix = self.similarity_service.build_similarity_matrix(
            framework_ids=framework_ids,
            only_assessable=True,
            threshold=threshold,
        )

        if not requirements:
            return []

        # Run hierarchical clustering
        clusters = self._hierarchical_clustering(
            requirements=requirements,
            similarity_matrix=similarity_matrix,
            threshold=threshold,
            min_cluster_size=min_cluster_size,
        )

        # Create cluster records
        created_clusters = []
        for cluster_requirements in clusters:
            cluster = self._create_cluster(
                requirements=cluster_requirements,
                cluster_type=cluster_type,
            )
            if cluster:
                created_clusters.append(cluster)

        self.db.commit()
        return created_clusters

    def _hierarchical_clustering(
        self,
        requirements: list[FrameworkRequirement],
        similarity_matrix: list[list[float]],
        threshold: float,
        min_cluster_size: int,
    ) -> list[list[FrameworkRequirement]]:
        """Perform hierarchical agglomerative clustering.

        Uses single-linkage clustering with early termination when
        maximum similarity falls below threshold.

        Args:
            requirements: List of requirements to cluster
            similarity_matrix: Pairwise similarity matrix
            threshold: Similarity threshold for merging
            min_cluster_size: Minimum cluster size

        Returns:
            List of clusters (each cluster is a list of requirements)
        """
        n = len(requirements)
        if n == 0:
            return []

        # Initialize each requirement as its own cluster
        clusters = [[i] for i in range(n)]
        active = set(range(n))  # Active cluster indices

        while len(active) > 1:
            # Find most similar pair of clusters
            best_sim = -1
            best_pair = None

            active_list = list(active)
            for i in range(len(active_list)):
                for j in range(i + 1, len(active_list)):
                    ci, cj = active_list[i], active_list[j]
                    sim = self._cluster_similarity(
                        clusters[ci], clusters[cj], similarity_matrix
                    )
                    if sim > best_sim:
                        best_sim = sim
                        best_pair = (ci, cj)

            # Stop if best similarity is below threshold
            if best_sim < threshold or best_pair is None:
                break

            # Merge clusters
            ci, cj = best_pair
            clusters[ci] = clusters[ci] + clusters[cj]
            active.remove(cj)

        # Convert indices back to requirements and filter by size
        result = []
        for i in active:
            if len(clusters[i]) >= min_cluster_size:
                cluster_reqs = [requirements[idx] for idx in clusters[i]]
                result.append(cluster_reqs)

        return result

    def _cluster_similarity(
        self,
        cluster1: list[int],
        cluster2: list[int],
        similarity_matrix: list[list[float]],
    ) -> float:
        """Compute similarity between two clusters using average linkage.

        Args:
            cluster1: Indices of requirements in first cluster
            cluster2: Indices of requirements in second cluster
            similarity_matrix: Pairwise similarity matrix

        Returns:
            Average similarity between cluster members
        """
        total_sim = 0.0
        count = 0

        for i in cluster1:
            for j in cluster2:
                total_sim += similarity_matrix[i][j]
                count += 1

        return total_sim / count if count > 0 else 0.0

    def _create_cluster(
        self,
        requirements: list[FrameworkRequirement],
        cluster_type: ClusterType,
    ) -> Optional[RequirementCluster]:
        """Create a cluster record with its members.

        Args:
            requirements: Requirements to include in the cluster
            cluster_type: Type of cluster

        Returns:
            Created RequirementCluster or None
        """
        if not requirements:
            return None

        # Generate cluster name from requirement codes
        codes = sorted([r.code for r in requirements])
        frameworks = set(r.framework_id for r in requirements)

        if len(codes) <= 3:
            name = " + ".join(codes)
        else:
            name = f"{codes[0]} + {len(codes) - 1} related requirements"

        # Generate description
        description = self._generate_cluster_description(requirements)

        # Calculate centroid embedding
        centroid = self._calculate_centroid(requirements)

        # Create cluster
        cluster = RequirementCluster(
            id=uuid.uuid4(),
            name=name,
            description=description,
            cluster_type=cluster_type.value,
            embedding_centroid=centroid,
            is_active=True,
            metadata={
                "requirement_count": len(requirements),
                "framework_count": len(frameworks),
                "framework_ids": [str(f) for f in frameworks],
            },
        )
        self.db.add(cluster)
        self.db.flush()

        # Add members
        for req in requirements:
            similarity = (
                self.similarity_service.cosine_similarity(req.embedding, centroid)
                if req.embedding and centroid
                else 0.0
            )

            member = RequirementClusterMember(
                id=uuid.uuid4(),
                cluster_id=cluster.id,
                requirement_id=req.id,
                similarity_score=similarity,
            )
            self.db.add(member)

        return cluster

    def _calculate_centroid(
        self,
        requirements: list[FrameworkRequirement],
    ) -> Optional[list[float]]:
        """Calculate the centroid embedding for a set of requirements.

        Args:
            requirements: Requirements to calculate centroid for

        Returns:
            Average embedding vector, or None if no embeddings available
        """
        embeddings = [
            r.embedding for r in requirements
            if r.embedding is not None
        ]

        if not embeddings:
            return None

        # Calculate element-wise average
        n = len(embeddings)
        dim = len(embeddings[0])

        centroid = [0.0] * dim
        for emb in embeddings:
            for i, val in enumerate(emb):
                centroid[i] += val / n

        return centroid

    def _generate_cluster_description(
        self,
        requirements: list[FrameworkRequirement],
    ) -> str:
        """Generate a description for a cluster.

        Args:
            requirements: Requirements in the cluster

        Returns:
            Generated description string
        """
        # Collect framework codes
        frameworks = defaultdict(list)
        for req in requirements:
            # Get framework through relationship or query
            if hasattr(req, 'framework') and req.framework:
                frameworks[req.framework.code].append(req.code)
            else:
                frameworks["Unknown"].append(req.code)

        parts = []
        for framework, codes in frameworks.items():
            parts.append(f"{framework}: {', '.join(codes)}")

        return "Cluster covering: " + "; ".join(parts)

    def get_cluster(self, cluster_id: uuid.UUID) -> Optional[RequirementCluster]:
        """Get a cluster by ID.

        Args:
            cluster_id: The cluster's UUID

        Returns:
            RequirementCluster or None
        """
        return (
            self.db.query(RequirementCluster)
            .filter(RequirementCluster.id == cluster_id)
            .first()
        )

    def get_cluster_members(
        self,
        cluster_id: uuid.UUID,
    ) -> list[tuple[FrameworkRequirement, float]]:
        """Get requirements in a cluster with their similarity scores.

        Args:
            cluster_id: The cluster's UUID

        Returns:
            List of (requirement, similarity_score) tuples
        """
        members = (
            self.db.query(RequirementClusterMember)
            .filter(RequirementClusterMember.cluster_id == cluster_id)
            .all()
        )

        result = []
        for member in members:
            requirement = (
                self.db.query(FrameworkRequirement)
                .filter(FrameworkRequirement.id == member.requirement_id)
                .first()
            )
            if requirement:
                result.append((requirement, member.similarity_score))

        return result

    def list_clusters(
        self,
        cluster_type: Optional[ClusterType] = None,
        is_active: bool = True,
    ) -> list[RequirementCluster]:
        """List all clusters with optional filters.

        Args:
            cluster_type: Filter by cluster type
            is_active: Filter by active status

        Returns:
            List of RequirementCluster objects
        """
        query = self.db.query(RequirementCluster)

        if cluster_type:
            query = query.filter(RequirementCluster.cluster_type == cluster_type.value)

        if is_active is not None:
            query = query.filter(RequirementCluster.is_active == is_active)

        return query.all()

    def get_requirement_cluster(
        self,
        requirement_id: uuid.UUID,
        cluster_type: Optional[ClusterType] = None,
    ) -> Optional[RequirementCluster]:
        """Get the cluster a requirement belongs to.

        Args:
            requirement_id: The requirement's UUID
            cluster_type: Optional filter by cluster type

        Returns:
            RequirementCluster or None if not in a cluster
        """
        query = (
            self.db.query(RequirementClusterMember)
            .filter(RequirementClusterMember.requirement_id == requirement_id)
        )

        if cluster_type:
            query = query.join(RequirementCluster).filter(
                RequirementCluster.cluster_type == cluster_type.value
            )

        member = query.first()
        if not member:
            return None

        return self.get_cluster(member.cluster_id)

    def delete_clusters(
        self,
        cluster_type: Optional[ClusterType] = None,
    ) -> int:
        """Delete all clusters (optionally filtered by type).

        Args:
            cluster_type: Optional filter by cluster type

        Returns:
            Number of clusters deleted
        """
        query = self.db.query(RequirementCluster)

        if cluster_type:
            query = query.filter(RequirementCluster.cluster_type == cluster_type.value)

        clusters = query.all()
        count = 0

        for cluster in clusters:
            # Delete members first
            self.db.query(RequirementClusterMember).filter(
                RequirementClusterMember.cluster_id == cluster.id
            ).delete()
            self.db.delete(cluster)
            count += 1

        self.db.commit()
        return count

    def estimate_interview_reduction(
        self,
        framework_ids: Optional[list[uuid.UUID]] = None,
    ) -> dict:
        """Estimate interview question reduction from clustering.

        Args:
            framework_ids: Frameworks to consider

        Returns:
            Dictionary with reduction statistics
        """
        # Count total assessable requirements
        query = self.db.query(FrameworkRequirement).filter(
            FrameworkRequirement.is_assessable == True
        )
        if framework_ids:
            query = query.filter(FrameworkRequirement.framework_id.in_(framework_ids))

        total_requirements = query.count()

        # Get all cluster memberships for assessable requirements
        cluster_query = self.db.query(RequirementCluster).filter(
            RequirementCluster.is_active == True
        )
        clusters = cluster_query.all()

        # Build a map of requirement -> best cluster (highest similarity)
        # This ensures each requirement is only counted once, even if
        # it appears in multiple clusters from repeated generation.
        requirement_best_cluster: dict[uuid.UUID, tuple[uuid.UUID, float]] = {}
        for cluster in clusters:
            members = (
                self.db.query(RequirementClusterMember)
                .filter(RequirementClusterMember.cluster_id == cluster.id)
                .all()
            )
            for member in members:
                existing = requirement_best_cluster.get(member.requirement_id)
                if existing is None or member.similarity_score > existing[1]:
                    requirement_best_cluster[member.requirement_id] = (
                        cluster.id,
                        member.similarity_score,
                    )

        # Only count requirements that are in the filtered set
        assessable_ids = {r.id for r in query.all()}
        effective_clusters: set[uuid.UUID] = set()
        clustered_requirement_ids: set[uuid.UUID] = set()
        for req_id, (cluster_id, _) in requirement_best_cluster.items():
            if req_id in assessable_ids:
                clustered_requirement_ids.add(req_id)
                effective_clusters.add(cluster_id)

        clustered_count = len(clustered_requirement_ids)
        unclustered_count = total_requirements - clustered_count
        total_clusters = len(effective_clusters)

        # Estimate: 1 question per effective cluster + 1 per unclustered requirement
        questions_with_clustering = total_clusters + unclustered_count
        questions_without_clustering = total_requirements

        reduction_pct = (
            (questions_without_clustering - questions_with_clustering)
            / questions_without_clustering * 100
            if questions_without_clustering > 0
            else 0
        )

        return {
            "total_requirements": total_requirements,
            "clustered_requirements": clustered_count,
            "unclustered_requirements": unclustered_count,
            "total_clusters": total_clusters,
            "questions_without_clustering": questions_without_clustering,
            "questions_with_clustering": questions_with_clustering,
            "reduction_percentage": round(reduction_pct, 1),
        }
