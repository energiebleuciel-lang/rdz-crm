/**
 * Hook to resolve which entities to load based on entityScope + optional local filter.
 * - super_admin BOTH → ['ZR7', 'MDL'] (or filtered)
 * - super_admin ZR7/MDL → [scope]
 * - non-super_admin → [user.entity]
 * Re-exports entityScope so pages refetch when scope changes.
 */
import { useCallback } from 'react';
import { useAuth } from './useAuth';

export function useEntityScope() {
  const { entityScope, isSuperAdmin, user } = useAuth();

  const getEntities = useCallback((localFilter) => {
    if (localFilter) return [localFilter];
    if (entityScope === 'BOTH') return ['ZR7', 'MDL'];
    return [entityScope || user?.entity || 'ZR7'];
  }, [entityScope, user]);

  return { entityScope, isSuperAdmin, getEntities };
}
