"use client";

import { queryKeys } from "@gridtrace/api-client";
import { DEMO_REGIONS } from "@gridtrace/testing/data";
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
} from "@gridtrace/ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { DatePicker } from "@/components/date-picker";
import { useApi } from "@/lib/client";

const schema = z.object({
  name: z.string().min(3, "Give the mission a descriptive name"),
  region_id: z.string().optional(),
  scheduled_date: z.string().optional(),
});

type Values = z.infer<typeof schema>;

export function CreateMissionForm() {
  const api = useApi();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: Values) =>
      api.inspectionMutations.createMission({
        name: values.name,
        region_id: values.region_id || null,
        scheduled_date: values.scheduled_date
          ? new Date(`${values.scheduled_date}T09:00:00.000Z`).toISOString()
          : null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.inspections.missions() });
      reset();
      setOpen(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4" />
          New mission
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit((v) => mutation.mutate(v))}>
          <DialogHeader>
            <DialogTitle>Create inspection mission</DialogTitle>
            <DialogDescription>
              Group prioritized cases into a field mission for a team.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="name">Mission name</Label>
              <Input id="name" placeholder="e.g. Noord — Week 25" {...register("name")} />
              {errors.name ? <p className="text-xs text-danger">{errors.name.message}</p> : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="region_id">Region</Label>
              <Select id="region_id" {...register("region_id")}>
                <option value="">Unassigned</option>
                {DEMO_REGIONS.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="scheduled_date">Scheduled date</Label>
              <Controller
                control={control}
                name="scheduled_date"
                render={({ field }) => (
                  <DatePicker
                    id="scheduled_date"
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="Select a date"
                  />
                )}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Creating…" : "Create mission"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
