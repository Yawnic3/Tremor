import { expect, test } from 'vitest';
import {percent} from './format';
test('percentage formatting preserves missing and zero',()=>{expect(percent(null)).toBe('—');expect(percent(0)).toBe('0.00%');expect(percent(-.0123)).toBe('-1.23%');expect(percent(.01)).toBe('+1.00%')});
