"use client";

import type { InspectionCase, InspectionOutcomeType } from "@gridtrace/contracts";
import { zodResolver } from "@hookform/resolvers/zod";
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
  Textarea,
} from "@gridtrace/ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useApi } from "@/lib/client";
import { applyOutcomeToCache } from "./case-cache";

const OUTCOMES: { value: InspectionOutcomeType; label: string }[] = [
  { value: "confirmed_theft", label: "Confirmed theft" },
  { value: "confirmed_meter_fault", label: "Confirmed meter fault" },
  { value: "no_issue_found", label: "No issue found" },
  { value: "inconclusive", label: "Inconclusive" },
];

const schema = z.object({
  outcome: z.enum(["confirmed_theft", "confirmed_meter_fault", "no_issue_found", "inconclusive"]),
  confirmed_loss_type: z.string().optional(),
  estimated_recovered_kwh: z.coerce.number().min(0).optional(),
  notes: z.string().optional(),
});

type Values = z.infer<typeof schema>;

export function SubmitOutcomeForm({
  missionId,
  inspectionCase,
  trigger,
}: {
  missionId: string;
  inspectionCase: InspectionCase;
  trigger: ReactNode;
}) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { outcome: "no_issue_found" },
  });

  const mutation = useMutation({
    mutationFn: (values: Values) =>
      api.inspectionMutations.submitOutcome(inspectionCase.id, {
        outcome: values.outcome,
        confirmed_loss_type: values.confirmed_loss_type || null,
        estimated_recovered_kwh: values.estimated_recovered_kwh ?? null,
        evidence: values.notes ? { notes: values.notes } : {},
      }),
    onSuccess: (outcome) => {
      applyOutcomeToCache(queryClient, missionId, outcome);
      setOpen(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit((v) => mutation.mutate(v))}>
          <DialogHeader>
            <DialogTitle>Record inspection outcome</DialogTitle>
            <DialogDescription>
              Submit the field-verified result for case {inspectionCase.id}.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="outcome">Outcome</Label>
              <Select id="outcome" {...register("outcome")}>
                {OUTCOMES.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirmed_loss_type">Confirmed loss type</Label>
              <Input
                id="confirmed_loss_type"
                placeholder="e.g. meter under-registration"
                {...register("confirmed_loss_type")}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="estimated_recovered_kwh">Estimated recovered (kWh)</Label>
              <Input
                id="estimated_recovered_kwh"
                type="number"
                min={0}
                step="any"
                {...register("estimated_recovered_kwh")}
              />
              {errors.estimated_recovered_kwh ? (
                <p className="text-xs text-danger">{errors.estimated_recovered_kwh.message}</p>
              ) : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="notes">Field notes</Label>
              <Textarea id="notes" rows={3} {...register("notes")} />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Submitting…" : "Submit outcome"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
