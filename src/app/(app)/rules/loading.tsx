import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function RulesLoading() {
  return (
    <div className="space-y-8">
      <div>
        <Skeleton className="h-9 w-24" />
        <Skeleton className="mt-2 h-4 w-64" />
      </div>
      <div className="flex gap-4">
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-10 w-32" />
      </div>
      <div className="space-y-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <div className="flex justify-between">
                <Skeleton className="h-5 w-48" />
                <Skeleton className="h-5 w-20 rounded-full" />
              </div>
              <Skeleton className="mt-3 h-4 w-full" />
              <Skeleton className="mt-2 h-3 w-3/4" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
