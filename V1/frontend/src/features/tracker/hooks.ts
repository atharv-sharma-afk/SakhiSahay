import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PeriodInput, SymptomInput } from "@/lib/types";

export function useTrackerData() {
  const periods = useQuery({ queryKey: ["tracker", "periods"], queryFn: api.periods });
  const symptoms = useQuery({ queryKey: ["tracker", "symptoms"], queryFn: api.symptoms });
  const catalogue = useQuery({ queryKey: ["tracker", "catalogue"], queryFn: api.symptomCatalogue, staleTime: Infinity });
  const insights = useQuery({ queryKey: ["insights"], queryFn: api.insights });
  const summary = useQuery({ queryKey: ["tracker", "summary"], queryFn: api.summary });
  return { periods, symptoms, catalogue, insights, summary };
}

export function useTrackerMutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["tracker"] });
    void qc.invalidateQueries({ queryKey: ["insights"] });
  };
  return {
    createPeriod: useMutation({ mutationFn: (d: PeriodInput) => api.createPeriod(d), onSuccess: invalidate }),
    updatePeriod: useMutation({ mutationFn: ({ id, data }: { id: string; data: PeriodInput }) => api.updatePeriod(id, data), onSuccess: invalidate }),
    deletePeriod: useMutation({ mutationFn: (id: string) => api.deletePeriod(id), onSuccess: invalidate }),
    createSymptom: useMutation({ mutationFn: (d: SymptomInput) => api.createSymptom(d), onSuccess: invalidate }),
    updateSymptom: useMutation({ mutationFn: ({ id, data }: { id: string; data: SymptomInput }) => api.updateSymptom(id, data), onSuccess: invalidate }),
    deleteSymptom: useMutation({ mutationFn: (id: string) => api.deleteSymptom(id), onSuccess: invalidate }),
    deleteAll: useMutation({ mutationFn: () => api.deleteAllData(), onSuccess: invalidate }),
  };
}
