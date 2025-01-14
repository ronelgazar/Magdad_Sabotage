import { Component, OnInit } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { DynamicFormComponent } from 'src/app/core/components/dynamic-form/dynamic-form.component';
import { CasesService } from 'src/app/core/services/cases.service';
import { FieldControlService } from 'src/app/core/services/field-control.service';
import { Router } from '@angular/router';
import { FormFieldBase } from 'src/app/core/utils/form-field-base';
@Component({
  selector: 'app-edit-case-screen',
  templateUrl: './edit-case-screen.component.html',
  styleUrls: ['./edit-case-screen.component.css'],
})
export class EditCaseScreenComponent implements OnInit {
  fields$: FormFieldBase<any>[];
  tags$: FormFieldBase<any>[];
  field$: FormFieldBase<string> = new FormFieldBase<string>();
  data: any;
  form!: FormGroup;
  caseData: any;
  caseQdata :any;
  caseQTags :any;
  saved_non_tags:boolean;
  constructor(private service: CasesService, private fcs: FieldControlService, private router: Router) {
    this.fields$ = service.getQuestions();
    this.tags$ = service.getTags();
    this.field$ = this.fields$[1];
    this.form = this.fcs.toFormGroup([this.field$]);
    this.caseData = JSON.parse(localStorage.getItem('caseQ') || '[]');
    this.saved_non_tags = false;
    localStorage.setItem('case', JSON.stringify(this.caseData))
    localStorage.removeItem('caseQ');
    this.splitAt("weapon_name",this.caseData);
    //split caseData to get only tags
  }
  splitAt(key: any, value: any) {
    // split object at key
    const [a, b]:[any, any] = [{}, {}];
    var after = false;
    Object.keys(value).forEach((k) => {
      //if key is found everything after is added to b and everything before is added to a
      if (k === key) {
        after = true;
      }
      if (after) {
        b[k] = value[k];
      } else {
        a[k] = value[k];
      }
    });
      console.log(a,b);
      this.caseQdata = a;
      this.caseQTags = b;

  }

  ngOnInit(): void {

  }

  onSubmit = (form: FormGroup, cb: (res: string) => void): void => {
    const formRawValue = form.getRawValue();
    if (!this.saved_non_tags){
      alert("קודם יש ללחוץ על עריכת תיק ללא תיוגים")
      return
    }
    this.caseData[1] = formRawValue;
    const data = {...this.caseData[0], ...this.caseData[1]};
    localStorage.setItem('case', JSON.stringify(data));
    this.service.updateCase(data).subscribe((res: any) => {
      console.log(res);
    });


    localStorage.setItem('case', JSON.stringify(data));
  };

  // sort form value by interface keys

  onFieldsInit = (form: FormGroup): void => {
    var value = this.caseQdata;

    // form.controls['exhibit_number'].setValue(this.data.exhibit_number);
    // go over this.data and set the value of the form

    // go ovewr JSON object and set the value of the form
    console.log(value);
  //   var value= this.caseData[0];

    for (let key in value) {
      if (form.controls[key]) {
        form.controls[key].setValue(value[key]);

      }
  }
  };
  onTagsInit = (form: FormGroup): void => {
    var value = this.caseQTags;
    for (let key in value) {
      if (form.controls[key]) {
        form.controls[key].setValue(value[key]);
      }
    }
  };

  onSave = (form: FormGroup, cb: (res: string) => void): void => {
    const formRawValue = form.getRawValue();
    delete formRawValue.navigator;
    this.caseData[0] = formRawValue;
    this.caseData[0].internal_number = JSON.parse(localStorage.getItem('internal_number') || '[]')
    const data = {...this.caseData[0], ...this.caseData[1]};
    localStorage.setItem('case', JSON.stringify(data));
    this.service.updateCase(data).subscribe((res: any) => {
      console.log(res);
    });
    this.saved_non_tags = true
  };

  generateDocxPage() {
    this.router.navigate(['/genLabForm']);
  }

}
