import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-oat-light text-clay-text',
        success: 'bg-green-50 text-green-700',
        destructive: 'bg-red-50 text-red-600',
        warning: 'bg-yellow-50 text-yellow-700',
        info: 'bg-blue-50 text-blue-700',
        outline: 'border border-clay-border text-clay-text',
        secret: 'bg-red-50 text-red-500',
      },
    },
    defaultVariants: { variant: 'default' },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
