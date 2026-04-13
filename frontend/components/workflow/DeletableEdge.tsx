'use client';

import {
  BaseEdge,
  type EdgeProps,
  getBezierPath,
} from '@xyflow/react';

import { useWorkflowStore } from '@/stores/workflowStore';

export function DeletableEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
}: EdgeProps) {
  const onEdgesChange = useWorkflowStore((s) => s.onEdgesChange);

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdgesChange([{ id, type: 'remove' }]);
  };

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      <foreignObject
        width={20}
        height={20}
        x={labelX - 10}
        y={labelY - 10}
        requiredExtensions="http://www.w3.org/1999/xhtml"
      >
        <button
          type="button"
          className="flex h-5 w-5 items-center justify-center rounded-full border border-clay-border bg-white text-[10px] text-warmSilver shadow-sm hover:border-red-300 hover:bg-red-50 hover:text-red-500"
          onClick={handleDelete}
          title="연결 삭제"
        >
          ✕
        </button>
      </foreignObject>
    </>
  );
}
