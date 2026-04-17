import * as React from 'react';
import { cn } from '@/lib/utils';

const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => {
    return (
      <select
        className={cn(
          'flex h-9 w-full appearance-none rounded-lg border border-clay-border bg-white px-3 py-1 text-sm text-clayBlack shadow-clay-0 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clay-accent focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Select.displayName = 'Select';

export { Select };
