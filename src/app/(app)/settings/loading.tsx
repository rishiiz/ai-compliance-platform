import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function SettingsLoading() {
  return (
    <div className="space-y-8">
      <div>
        <Skeleton className="h-9 w-28" />
        <Skeleton className="mt-2 h-4 w-80" />
      </div>
      <Skeleton className="h-10 w-full max-w-2xl" />
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-36" />
          <Skeleton className="mt-2 h-4 w-64" />
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <Skeleton className="h-4 w-24" />
            <Skeleton className="mt-2 h-10 w-full" />
          </div>
          <div>
            <Skeleton className="h-4 w-32" />
            <Skeleton className="mt-2 h-2 w-full" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
