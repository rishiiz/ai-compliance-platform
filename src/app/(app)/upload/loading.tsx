import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function UploadLoading() {
  return (
    <div className="space-y-8">
      <div>
        <Skeleton className="h-9 w-40" />
        <Skeleton className="mt-2 h-4 w-72" />
      </div>
      <Card>
        <CardContent className="p-12">
          <div className="flex flex-col items-center gap-4">
            <Skeleton className="h-24 w-24 rounded-full" />
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
