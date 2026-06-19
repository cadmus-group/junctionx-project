"use client";

import { queryKeys } from "@gridtrace/api-client";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Input,
  Label,
  Select,
} from "@gridtrace/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useApi } from "@/lib/client";
import { appendCaseToCache } from "./case-cache";

export function AddToMissionDialog({
  customerId,
  riskScoreId,
  recommendedAction,
  trigger,
}: {
  customerId: string;
  riskScoreId?: string | null;
  recommendedAction?: string | null;
  trigger: ReactNode;
}) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [missionId, setMissionId] = useState<string>("");
  const [newMissionName, setNewMissionName] = useState("");
  const [done, setDone] = useState(false);

  const missionsQuery = useQuery({ ...api.inspections.missions(), enabled: open });

  const mutation = useMutation({
    mutationFn: async () => {
      let targetMission = missionId;
      if (!targetMission) {
        const mission = await api.inspectionMutations.createMission({
          name: newMissionName || `Mission for ${customerId}`,
        });
        targetMission = mission.id;
      }
      const created = await api.inspectionMutations.addCase(targetMission, {
        customer_id: customerId,
        risk_score_id: riskScoreId ?? null,
        recommended_action: recommendedAction ?? null,
      });
      return { missionId: targetMission, created };
    },
    onSuccess: ({ missionId: targetMission, created }) => {
      appendCaseToCache(queryClient, targetMission, created);
      void queryClient.invalidateQueries({ queryKey: queryKeys.inspections.missions() });
      setDone(true);
    },
  });

  const missions = missionsQuery.data?.items ?? [];

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) {
          setDone(false);
          mutation.reset();
        }
      }}
    >
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add to inspection mission</DialogTitle>
          <DialogDescription>
            Queue this customer for on-site inspection. No action is taken without field
            confirmation.
          </DialogDescription>
        </DialogHeader>

        {done ? (
          <p className="text-sm text-success">Case added to the mission queue.</p>
        ) : (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="mission">Existing mission</Label>
              <Select
                id="mission"
                value={missionId}
                onChange={(e) => setMissionId(e.target.value)}
              >
                <option value="">Create a new mission…</option>
                {missions.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </Select>
            </div>
            {!missionId ? (
              <div className="space-y-1.5">
                <Label htmlFor="mission-name">New mission name</Label>
                <Input
                  id="mission-name"
                  placeholder="e.g. De Pijp — Week 25"
                  value={newMissionName}
                  onChange={(e) => setNewMissionName(e.target.value)}
                />
              </div>
            ) : null}
            {mutation.isError ? (
              <p className="text-sm text-danger">Could not add the case. Try again.</p>
            ) : null}
          </div>
        )}

        <DialogFooter>
          {done ? (
            <Button onClick={() => setOpen(false)}>Close</Button>
          ) : (
            <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
              {mutation.isPending ? "Adding…" : "Add case"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
