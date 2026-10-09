"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { TaskState } from "@/types/job";

const POLL_MS = 1500;

/** Starts or resumes a background task (scan or triage) and polls its progress until it finishes. */
export function useScanTask(onFinished: (task: TaskState) => void) {
  const [task, setTask] = useState<TaskState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onFinishedRef = useRef(onFinished);

  useEffect(() => {
    onFinishedRef.current = onFinished;
  }, [onFinished]);

  const poll = useCallback(async (taskId: string) => {
    try {
      const state = await api.task(taskId);
      setTask(state);
      if (state.status === "running") {
        timer.current = setTimeout(() => poll(taskId), POLL_MS);
      } else if (state.status === "error") {
        setError(state.error ?? "Falha na busca");
        setTask(null);
      } else {
        onFinishedRef.current(state); // done or cancelled: what was found is already saved
      }
    } catch (e) {
      setError((e as Error).message);
      setTask(null);
    }
  }, []);

  const follow = useCallback(
    (state: TaskState) => {
      setError(null);
      setTask(state);
      poll(state.task_id);
    },
    [poll],
  );

  const start = useCallback(
    async (rangeHours: number) => {
      try {
        follow(await api.startScan(rangeHours));
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [follow],
  );

  const resumeIfRunning = useCallback(async () => {
    const running = await api.runningTask().catch(() => null);
    if (running) follow(running);
  }, [follow]);

  const cancel = useCallback(async () => {
    if (!task) return;
    try {
      setTask(await api.cancelTask(task.task_id));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [task]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  return { task, running: task?.status === "running", error, start, follow, cancel, resumeIfRunning };
}
