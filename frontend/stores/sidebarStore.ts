'use client';

import { create } from 'zustand';

type PanelType = 'components' | 'mcp' | 'runlog';

interface SidebarStore {
  isOpen: boolean;
  activePanel: PanelType | null;
  toggle: (panel: PanelType) => void;
  close: () => void;
}

export const useSidebarStore = create<SidebarStore>((set) => ({
  isOpen: true,
  activePanel: 'components' as PanelType,

  toggle: (panel) =>
    set((state) => {
      if (state.isOpen && state.activePanel === panel) {
        return { isOpen: false, activePanel: null };
      }
      return { isOpen: true, activePanel: panel };
    }),

  close: () => set({ isOpen: false, activePanel: null }),
}));
