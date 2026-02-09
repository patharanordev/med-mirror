import { render, screen, fireEvent } from '@testing-library/react';
import { Controls } from '../Controls';
import '@testing-library/jest-dom';

describe('Controls Component', () => {
    const mockProps = {
        isStreaming: false,
        onToggleCamera: jest.fn(),
        isAuto: false,
        onToggleAuto: jest.fn(),
        isVAD: false,
        onToggleVAD: jest.fn(),
        onManualCapture: jest.fn(),
    };

    test('renders all buttons', () => {
        render(<Controls {...mockProps} />);
        expect(screen.getByText('Start Camera')).toBeInTheDocument();
        expect(screen.getByText('Analyze')).toBeInTheDocument();
        expect(screen.getByText('Auto')).toBeInTheDocument();
        expect(screen.getByText('VAD')).toBeInTheDocument();
    });

    test('toggles camera button text and style based on isStreaming', () => {
        const { rerender } = render(<Controls {...mockProps} />);
        const cameraButton = screen.getByText('Start Camera').closest('button');
        expect(cameraButton).toHaveClass('bg-white/10');

        rerender(<Controls {...mockProps} isStreaming={true} />);
        expect(screen.getByText('Stop Camera')).toBeInTheDocument();
        const activeCameraButton = screen.getByText('Stop Camera').closest('button');
        expect(activeCameraButton).toHaveClass('bg-red-500/20');
    });

    test('calls handler functions on click', () => {
        render(<Controls {...mockProps} isStreaming={true} />); // enable streaming to enable other buttons

        fireEvent.click(screen.getByText('Stop Camera'));
        expect(mockProps.onToggleCamera).toHaveBeenCalledTimes(1);

        fireEvent.click(screen.getByText('Analyze'));
        expect(mockProps.onManualCapture).toHaveBeenCalledTimes(1);

        fireEvent.click(screen.getByText('Auto'));
        expect(mockProps.onToggleAuto).toHaveBeenCalledTimes(1);

        fireEvent.click(screen.getByText('VAD'));
        expect(mockProps.onToggleVAD).toHaveBeenCalledTimes(1);
    });

    test('disables Analyze and Auto buttons when not streaming', () => {
        render(<Controls {...mockProps} isStreaming={false} />);

        expect(screen.getByText('Analyze').closest('button')).toBeDisabled();
        expect(screen.getByText('Auto').closest('button')).toBeDisabled();
    });
});
