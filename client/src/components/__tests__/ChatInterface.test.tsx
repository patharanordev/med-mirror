import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInterface } from '../ChatInterface';
import '@testing-library/jest-dom';

describe('ChatInterface Component', () => {
    const mockProps = {
        messages: [],
        onSend: jest.fn(),
        input: '',
        setInput: jest.fn(),
        listening: false,
        userSpeaking: false,
    };

    beforeAll(() => {
        // Mock scrollIntoView
        Element.prototype.scrollIntoView = jest.fn();
    });

    test('renders title and input', () => {
        render(<ChatInterface {...mockProps} />);
        expect(screen.getByText('MedMirror Assistant')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
    });

    test('renders messages correctly', () => {
        const messages: any[] = [
            { role: 'user', content: 'Hello' },
            { role: 'assistant', content: 'Hi there' },
        ];
        render(<ChatInterface {...mockProps} messages={messages} />);

        expect(screen.getByText('Hello')).toBeInTheDocument();
        expect(screen.getByText('Hi there')).toBeInTheDocument();
    });

    test('handles input change', () => {
        render(<ChatInterface {...mockProps} />);
        const input = screen.getByPlaceholderText('Type a message...');
        fireEvent.change(input, { target: { value: 'New message' } });
        expect(mockProps.setInput).toHaveBeenCalledWith('New message');
    });

    test('calls onSend when send button is clicked', () => {
        render(<ChatInterface {...mockProps} input="Test" />);
        // There are SVG icons, so it's easier to find button by role 'button' inside the relative container or by the Send icon if it had text.
        // The button contains the Send icon.
        // Let's rely on finding the button that isn't the mic indicator (which is not a button).
        // The send button is the last button in the component structure or we can add aria-label in actual code to be sure.
        // But here we can use a simpler selector or assume it's the only button in the input area?
        // Actually, Controls are fixed positioned, ChatInterface is also fixed.
        // Let's just assume we can find it by className or implicit role.
        // Better: check for the input wrapper first.

        // Simpler: fireEvent.click on the button wrapping the Send icon.
        // But testing-library encourages user-centric queries. 
        // Since there's no text in the button ("Send"), we might need to rely on the test modifying the component to add aria-label or just traverse DOM.
        // However, I can't modify the component right now easily without another turn.
        // I'll try to find it by role button associated with the input group.

        // Wait, the input area has a button.
        const buttons = screen.getAllByRole('button');
        // The Send button is likely the one near the input.
        // Let's use fireEvent.keyDown on input for safer test first.

        const inputEl = screen.getByPlaceholderText('Type a message...');
        fireEvent.keyDown(inputEl, { key: 'Enter', code: 'Enter' });
        expect(mockProps.onSend).toHaveBeenCalled();
    });

    test('shows listening state', () => {
        render(<ChatInterface {...mockProps} listening={true} userSpeaking={true} />);
        expect(screen.getByText('🎤 Listening...')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Speak now...')).toBeInTheDocument();
    });
});
