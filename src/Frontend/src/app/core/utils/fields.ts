import { DatePipe, formatDate } from '@angular/common';
import { PipeTransform } from '@angular/core';
import { FormFieldBase } from './form-field-base';
import { Moment } from 'moment';
export class CheckboxField extends FormFieldBase<string> {
  override controlType = 'checkbox';
}

export class DatePickerField extends FormFieldBase<string>{
  override controlType = 'datepicker';
  }

export class DropdownField extends FormFieldBase<string> {
  override controlType = 'dropdown';
}

export class TextboxField extends FormFieldBase<string> {
  override controlType = 'textbox';
}
export class SeparatorField extends FormFieldBase<string> {
  override controlType = 'separator';
}
export class ButtonField extends FormFieldBase<string> {
  override controlType = 'button';
}
