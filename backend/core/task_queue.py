"""
Task Queue System

This module provides a simple task management system for running
background tasks like surveys and exports. Can be extended to use
Celery for production deployments.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from enum import Enum
import threading
import queue
import time
import uuid
from loguru import logger


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Types of background tasks"""
    SURVEY = "survey"
    EXPORT = "export"
    SCAN = "scan"
    ANALYSIS = "analysis"


@dataclass
class TaskInfo:
    """Information about a background task"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_type': self.task_type.value,
            'status': self.status.value,
            'progress': self.progress,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'metadata': self.metadata
        }


class TaskWorker(threading.Thread):
    """Worker thread for executing tasks"""

    def __init__(self, task_queue: queue.Queue, task_registry: Dict[str, TaskInfo]):
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.task_registry = task_registry
        self._stop_event = threading.Event()

    def run(self):
        """Main worker loop"""
        while not self._stop_event.is_set():
            try:
                # Get task with timeout
                task = self.task_queue.get(timeout=1.0)
                if task is None:
                    continue

                task_id, func, args, kwargs = task
                task_info = self.task_registry.get(task_id)

                if task_info is None:
                    continue

                # Update status
                task_info.status = TaskStatus.RUNNING
                task_info.started_at = datetime.utcnow()

                try:
                    # Execute task
                    result = func(*args, **kwargs)
                    task_info.result = result
                    task_info.status = TaskStatus.COMPLETED
                    task_info.progress = 100.0

                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    task_info.error = str(e)
                    task_info.status = TaskStatus.FAILED

                finally:
                    task_info.completed_at = datetime.utcnow()
                    self.task_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    def stop(self):
        """Stop the worker"""
        self._stop_event.set()


class TaskManager:
    """
    Manages background task execution.

    Provides a simple interface for:
    - Submitting background tasks
    - Checking task status
    - Cancelling tasks
    - Getting task results
    """

    def __init__(self, num_workers: int = 2):
        """
        Initialize task manager.

        Args:
            num_workers: Number of worker threads
        """
        self.task_queue: queue.Queue = queue.Queue()
        self.task_registry: Dict[str, TaskInfo] = {}
        self.workers: List[TaskWorker] = []
        self._lock = threading.Lock()

        # Start workers
        for _ in range(num_workers):
            worker = TaskWorker(self.task_queue, self.task_registry)
            worker.start()
            self.workers.append(worker)

        logger.info(f"Task manager initialized with {num_workers} workers")

    def submit(
        self,
        task_type: TaskType,
        func: Callable,
        *args,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Submit a task for background execution.

        Args:
            task_type: Type of task
            func: Function to execute
            *args: Positional arguments for function
            metadata: Optional task metadata
            **kwargs: Keyword arguments for function

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        task_info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            metadata=metadata or {}
        )

        with self._lock:
            self.task_registry[task_id] = task_info

        self.task_queue.put((task_id, func, args, kwargs))
        logger.info(f"Task submitted: {task_id} ({task_type.value})")

        return task_id

    def get_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status by ID"""
        return self.task_registry.get(task_id)

    def get_all_tasks(self, task_type: Optional[TaskType] = None) -> List[TaskInfo]:
        """Get all tasks, optionally filtered by type"""
        with self._lock:
            tasks = list(self.task_registry.values())

        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]

        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def cancel(self, task_id: str) -> bool:
        """
        Cancel a pending task.

        Note: Cannot cancel running tasks.

        Returns:
            True if task was cancelled
        """
        task_info = self.task_registry.get(task_id)
        if task_info is None:
            return False

        if task_info.status == TaskStatus.PENDING:
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = datetime.utcnow()
            logger.info(f"Task cancelled: {task_id}")
            return True

        return False

    def update_progress(self, task_id: str, progress: float) -> None:
        """Update task progress (0-100)"""
        task_info = self.task_registry.get(task_id)
        if task_info:
            task_info.progress = min(100.0, max(0.0, progress))

    def cleanup_completed(self, max_age_seconds: float = 3600) -> int:
        """
        Remove completed tasks older than max_age.

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            Number of tasks removed
        """
        now = datetime.utcnow()
        removed = 0

        with self._lock:
            to_remove = []
            for task_id, task_info in self.task_registry.items():
                if task_info.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    if task_info.completed_at:
                        age = (now - task_info.completed_at).total_seconds()
                        if age > max_age_seconds:
                            to_remove.append(task_id)

            for task_id in to_remove:
                del self.task_registry[task_id]
                removed += 1

        if removed:
            logger.info(f"Cleaned up {removed} old tasks")

        return removed

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the task manager.

        Args:
            wait: Wait for pending tasks to complete
        """
        logger.info("Shutting down task manager...")

        if wait:
            self.task_queue.join()

        for worker in self.workers:
            worker.stop()
            worker.join(timeout=2.0)

        logger.info("Task manager shutdown complete")


# Global task manager instance
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get the global task manager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


# Convenience functions for common tasks
def submit_survey_task(survey_id: int, device_id: int, **kwargs) -> str:
    """
    Submit a survey task.

    Args:
        survey_id: Survey ID to execute
        device_id: Device ID to use
        **kwargs: Additional survey parameters

    Returns:
        Task ID
    """
    from .survey_manager import get_survey_manager, SurveyConfig, GPSMode

    def run_survey():
        manager = get_survey_manager()
        config = SurveyConfig(
            survey_id=survey_id,
            device_id=device_id,
            **kwargs
        )
        return manager.start_survey(config)

    return get_task_manager().submit(
        TaskType.SURVEY,
        run_survey,
        metadata={'survey_id': survey_id, 'device_id': device_id}
    )


def submit_export_task(
    survey_id: int,
    export_type: str,
    output_path: str,
    **kwargs
) -> str:
    """
    Submit an export task.

    Args:
        survey_id: Survey to export
        export_type: Export format ('csv' or 'geopackage')
        output_path: Output file path
        **kwargs: Additional export parameters

    Returns:
        Task ID
    """
    def run_export():
        # Import here to avoid circular imports
        if export_type == 'csv':
            from ..api.routes.export import run_csv_export
            import asyncio
            asyncio.run(run_csv_export(kwargs.get('job_id', 0), survey_id))
        elif export_type == 'geopackage':
            from ..api.routes.export import run_geopackage_export
            import asyncio
            asyncio.run(run_geopackage_export(kwargs.get('job_id', 0), survey_id, kwargs))

    return get_task_manager().submit(
        TaskType.EXPORT,
        run_export,
        metadata={'survey_id': survey_id, 'export_type': export_type}
    )
