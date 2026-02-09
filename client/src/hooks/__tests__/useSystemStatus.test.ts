import { renderHook, act, waitFor } from '@testing-library/react';
import { useSystemStatus } from '../useSystemStatus';

// Mock global fetch
global.fetch = jest.fn();

describe('useSystemStatus', () => {
    beforeEach(() => {
        jest.useFakeTimers();
        (global.fetch as jest.Mock).mockClear();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    it('should return initial loading status', () => {
        // Mock fetch to return pending promise initially
        (global.fetch as jest.Mock).mockImplementation(() => new Promise(() => { }));

        const { result } = renderHook(() => useSystemStatus());

        expect(result.current).toEqual({
            stt: 'loading',
            llm: 'loading',
        });
    });

    it('should update status when API returns success', async () => {
        const mockResponse = {
            stt_ready: true,
            llm_ready: true,
            llm_model: 'med-gemma',
        };

        (global.fetch as jest.Mock).mockResolvedValue({
            ok: true,
            json: async () => mockResponse,
        });

        const { result } = renderHook(() => useSystemStatus());

        // Fast-forward initial check
        await act(async () => {
            jest.advanceTimersByTime(0); // For immediate effect if needed, but fetch is async
        });

        // Wait for the update
        await waitFor(() => {
            expect(result.current).toEqual({
                stt: 'ready',
                llm: 'ready',
                modelName: 'med-gemma',
            });
        });
    });

    it('should handle API errors gracefully', async () => {
        (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
        const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

        const { result } = renderHook(() => useSystemStatus());

        // Wait for potential effects
        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalled();
        });

        // Should remain in loading state (default) on error if it was loading
        expect(result.current).toEqual({
            stt: 'loading',
            llm: 'loading',
        });

        consoleSpy.mockRestore();
    });
});
